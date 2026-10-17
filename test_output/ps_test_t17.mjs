// ParticleSystem.js emitSpell/既存API 検証ハーネス (PIXIスタブ) — T17検証用・実行後に削除
globalThis.window = globalThis;
class G {
  constructor() { this.scale = { set() {} }; this.x = 0; this.y = 0; this.rotation = 0; this.alpha = 1; this.visible = true; }
  clear() { return this; }
  beginFill() { return this; }
  endFill() { return this; }
  drawCircle() { return this; }
  drawRect() { return this; }
  drawPolygon() { return this; }
  lineStyle() { return this; }
  moveTo() { return this; }
  lineTo() { return this; }
  destroy() {}
}
globalThis.PIXI = {
  BLEND_MODES: { ADD: 1 },
  Graphics: G,
  Container: class { addChild(...c) { return c.length; } removeChild() {} removeChildren() {} },
};
const { ParticleSystem } = await import('file:///home/herbmatsui/narou/demos/lib/ParticleSystem.js');

const ps = new ParticleSystem({}, new PIXI.Container());

// 1) 既存emit: ランダム速度パスが壊れていないか
ps.emit({ type: 'dust', x: 10, y: 10, count: 5, speed: 0.5 });
if (ps.particles.length !== 5) throw new Error('emit broken: ' + ps.particles.length);
const dust = ps.particles[0];
if (!(Number.isFinite(dust.vx) && Number.isFinite(dust.vy))) throw new Error('dust velocity NaN');
console.log('1) emit dust OK count=5 finite velocity');

// 2) 既存emitEffect
ps.emitEffect('hit', 0, 0, 3);
if (ps.getActiveCount() !== 11) throw new Error('emitEffect broken: ' + ps.getActiveCount());
console.log('2) emitEffect hit OK active=11');

// 3) emitSpell 5属性+フォールバック: L1即時24 / 遅延レイヤー発火
for (const name of ['fire', 'ice', 'lightning', 'heal', 'teleport', 'magic', 'unknown']) {
  ps.clear();
  ps.emitSpell(name, 100, 100);
  const l1 = ps.particles.length;
  if (l1 !== 24) throw new Error(name + ' L1 count: ' + l1);
  if (ps.scheduledEmits.length !== 5) throw new Error(name + ' scheduled: ' + ps.scheduledEmits.length);
  for (let i = 0; i < 20; i++) ps.update(1 / 60); // 0.33s
  const l2 = ps.particles.length;
  for (let i = 0; i < 50; i++) ps.update(1 / 60); // 1.16s
  const l3 = ps.particles.length;
  console.log(`3) ${name}: L1=${l1} @0.33s=${l2} @1.16s=${l3}`);
  if (l2 < 40) throw new Error(name + ' L2/L3 not fired: ' + l2);
}
// 遅延キューが最後まで空になること
for (let i = 0; i < 200; i++) ps.update(1 / 60);
if (ps.scheduledEmits.length !== 0) throw new Error('scheduled not drained');
console.log('3b) scheduled queue drained');

// 4) maxParticles 500維持
ps.clear();
ps.emit({ type: 'dust', x: 0, y: 0, count: 600, speed: 0.5 });
if (ps.particles.length > ps.maxParticles) throw new Error('cap broken');
console.log('4) maxParticles cap OK:', ps.particles.length, '<=', ps.maxParticles);

// 5) L1収束ベクトル: スポーン位置と速度が逆方向
ps.clear();
ps.emitSpell('fire', 0, 0);
let converging = 0;
for (const p of ps.particles) {
  if (p.x * p.vx + p.y * p.vy < 0) converging++;
}
if (converging !== 24) throw new Error('converge broken: ' + converging);
console.log('5) converge vectors OK: 24/24');

// 6) L3光条: 12本・速度方向へ回転固定・高速
ps.clear();
ps.emitSpell('lightning', 0, 0);
for (let i = 0; i < 25; i++) ps.update(1 / 60); // 0.417s
const streaks = ps.particles.filter(p => p.rotationSpeed === 0 && Math.hypot(p.vx, p.vy) > 300);
if (streaks.length !== 12) throw new Error('streak count: ' + streaks.length);
for (const s of streaks) {
  const err = Math.abs(Math.atan2(s.vy, s.vx) - s.rotation);
  if (err > 1e-6) throw new Error('rotation not aligned');
}
console.log('6) streaks OK: 12 aligned fast');

// 7) L4リング: 0.8s時点で L2(32) + リング3連(72) = 104 生存 (L1/L3は消滅済み)
ps.clear();
ps.emitSpell('fire', 0, 0);
for (let i = 0; i < 48; i++) ps.update(1 / 60);
if (ps.particles.length !== 104) throw new Error('layer composition: ' + ps.particles.length);
// リングは放射状: 速度方向と位置方向が同方向
let radial = 0;
for (const p of ps.particles) {
  if (p.x * p.vx + p.y * p.vy > 0) radial++;
}
if (radial !== 104) throw new Error('radial broken: ' + radial);
console.log('7) L2+rings OK: 104 alive, all radial');

// 8) clear()でスケジュールも空に
ps.emitSpell('ice', 0, 0);
ps.clear();
if (ps.scheduledEmits.length !== 0 || ps.particles.length !== 0) throw new Error('clear broken');
console.log('8) clear OK');

console.log('ALL PARTICLE TESTS PASSED');
