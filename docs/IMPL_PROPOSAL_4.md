# 提案4: DDGI/LPV の GPU 移植または削除判断 — 実装計画書

## 現状分析

`core/gi.py` には DDGI（Dynamic Diffuse Global Illumination）と LPV（Light Propagation Volumes）の **CPU実装のみ** 存在。NumPyベースのプローブグリッド計算で、GPU連携・レイトレーシング・RSM（Reflective Shadow Maps）なし。実質デッドコード。

## 判断: **削除推奨（選択肢B）**

理由: 2Dローグライクに DDGI は過剰。`LightingSystem` の乗算/加算ブレンド + 簡易 SSAO で十分。コード削減・保守性向上。

---

## 実装ステップ（全12ステップ）

### Phase 1: 現状確認・影響調査（Step 1-3）

#### Step 1: gi.py 全量読解・依存関係確認
```bash
# 実行
cat core/gi.py
grep -r "from core.gi" --include="*.py"
grep -r "import.*gi" --include="*.py"
```
- クラス: `DDGIProbes`, `LPV`, `RSM`
- 公開関数: `create_ddgi_probes()`, `create_lpv()`, `update_gi()`
- どこから呼ばれているか全特定

#### Step 2: 呼び出し箇所の実態確認
```bash
grep -rn "DDGI\|LPV\|RSM\|create_ddgi\|create_lpv\|update_gi" --include="*.py"
```
- 実際にインスタンス化・更新されているか
- テストコードのみか、本番コードからも呼ばれているか

#### Step 3: パフォーマンス測定（参考値）
```python
# 簡易ベンチマーク
import time, numpy as np
from core.gi import create_ddgi_probes, create_lpv

probes = create_ddgi_probes(32, 32, 32)  # 32^3 probes
start = time.time()
for _ in range(10):
    probes.update(np.random.rand(32,32,32,3))
print(f"DDGI update: {(time.time()-start)/10*1000:.1f}ms")

lpv = create_lpv(64, 64, 64)
start = time.time()
for _ in range(10):
    lpv.propagate(np.random.rand(64,64,64,3))
print(f"LPV propagate: {(time.time()-start)/10*1000:.1f}ms")
```
- 期待: 数百ms〜秒オーダー（実用不可）

---

### Phase 2: 削除実行（Step 4-8）

#### Step 4: gi.py 完全削除
```bash
rm core/gi.py
```

#### Step 5: インポート除去・置換
```bash
# 該当ファイルでインポート行削除
grep -rl "from core.gi import\|import.*gi" --include="*.py" | xargs -I{} sed -i '/gi/d' {}
```
- `core/__init__.py` からもエクスポート削除

#### Step 6: 代替実装: 簡易 SSAO（Screen Space Ambient Occlusion）
```python
# core/lighting.py に追加
class SimpleSSAO:
    """法線ベース擬似 SSAO（深度バッファ不要）"""
    def __init__(self, width: int, height: int, radius: int = 2):
        self.width = width
        self.height = height
        self.radius = radius
        self.kernel = self._generate_kernel(16)
        self.noise = self._generate_noise(4, 4)
    
    def _generate_kernel(self, n: int) -> List[Tuple[float,float,float]]:
        import random, math
        kernel = []
        for i in range(n):
            vec = (random.uniform(-1,1), random.uniform(-1,1), random.uniform(0,1))
            # ヘミサンプリング
            length = math.sqrt(sum(v*v for v in vec))
            kernel.append((vec[0]/length, vec[1]/length, vec[2]/length))
        return kernel
    
    def _generate_noise(self, w: int, h: int) -> List[List[Tuple[float,float]]]:
        import random
        return [[(random.uniform(-1,1), random.uniform(-1,1)) for _ in range(w)] for _ in range(h)]
    
    def compute(self, normal_buffer: np.ndarray) -> np.ndarray:
        """法線バッファから AO 値計算（簡易版）"""
        # 実装は簡易化: 法線のばらつきから擬似的に AO 推定
        # 実際には深度バッファ必要だが、2Dでは法線のみで近似
        ao = np.ones((self.height, self.width), dtype=np.float32)
        # 簡易実装: エッジ検出で暗くする程度
        from scipy import ndimage
        edges = ndimage.sobel(normal_buffer[...,0]) + ndimage.sobel(normal_buffer[...,1])
        ao = np.clip(1.0 - edges * 0.5, 0.3, 1.0)
        return ao
```

#### Step 7: ライティングパスに SSAO 統合
```python
# TerminalLightingSystem.render_pass() 内で呼び出し
def render_pass(self, console, cam_x, cam_y, view_w, view_h, visible, explored, time):
    # 既存の apply_lighting_to_tiles...
    # 追加: SSAO 適用
    if hasattr(self, 'ssao') and self.ssao:
        # 法線バッファがあれば適用
        pass  # 将来拡張用
```

#### Step 8: 不要ファイル・テスト削除
```bash
# gi 関連テストがあれば削除
find . -name "*test*gi*" -o -name "*gi*test*" | xargs rm -f
```

---

### Phase 3: 検証・ドキュメント（Step 9-12）

#### Step 9: 全テスト実行・回帰確認
```bash
python -m pytest tools/ -v
python tools/test_lighting.py
python tools/test_particles.py
python tools/test_entity_parity.py
python tools/test_attack_anim.py
```
- エラーなしを確認

#### Step 10: パフォーマンス比較
```bash
# 削除前後の FPS 測定（ゲーム起動して測定）
# 期待: 変化なし、またはわずかに向上
```

#### Step 11: ドキュメント更新
```markdown
# docs/GI_REMOVAL.md
## DDGI/LPV 削除記録
- 日付: 2026-08-19
- 理由: 2Dローグライクに過剰、CPU実装のみで実用不可
- 代替: 簡易 SSAO（将来実装予定）
- 削除ファイル: core/gi.py
- 影響: なし（未使用だったため）
```

#### Step 12: 最終確認・完了報告
```bash
git status
git diff --stat
# core/gi.py 削除、インポート除去のみであることを確認
```

---

## 完了判定基準

- [ ] `core/gi.py` 完全削除
- [ ] 全インポート除去完了
- [ ] 全テストパス
- [ ] FPS 低下なし
- [ ] ドキュメント更新完了

---

## リスク・対策

| リスク | 対策 |
|--------|------|
| 実はどこかで使われていた | Step 2 で徹底確認、テストで検出 |
| 将来「やっぱり欲しい」と言われる | Git 履歴から復元可能、ドキュメントに判断理由記録 |