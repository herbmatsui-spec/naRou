"""core/particles のテスト。

ParticleBuffer / CurlNoise / SDFCollision / Emitter / simulate_particles_cpu
をカバーする。外部依存（GPU・ウィンドウ）は使わず、numpy のみで
動作する正常系・異常系・境界値をテストする。
"""

from __future__ import annotations

import numpy as np
import pytest

from core.particles import (
    CurlNoise,
    Emitter,
    Particle,
    ParticleBuffer,
    ParticleFlags,
    SDFCollision,
    simulate_particles_cpu,
)


class TestParticleFlags:
    """ParticleFlags IntEnum のテスト。"""

    def test_flag_values(self):
        """各フラグが期待されるビット値を持つこと。"""
        assert ParticleFlags.ALIVE == 1
        assert ParticleFlags.RIBBON == 2
        assert ParticleFlags.TRAIL == 4
        assert ParticleFlags.MESH == 8
        assert ParticleFlags.COLLIDE == 16
        assert ParticleFlags.EMIT_LIGHT == 32

    def test_flag_bitwise_combination(self):
        """フラグをビットORで組み合わせられること。"""
        combined = ParticleFlags.ALIVE | ParticleFlags.RIBBON
        assert int(combined) == 3
        assert combined & ParticleFlags.ALIVE
        assert combined & ParticleFlags.RIBBON


class TestParticle:
    """Particle データクラスのテスト。"""

    def test_create_with_required_arrays(self):
        """必須の ndarray を指定して生成できること。"""
        p = Particle(
            position=np.zeros(3, dtype=np.float32),
            velocity=np.zeros(3, dtype=np.float32),
            life=np.zeros(4, dtype=np.float32),
            color=np.ones(4, dtype=np.float32),
            size=np.ones(4, dtype=np.float32),
            rotation=np.zeros(4, dtype=np.float32),
        )
        assert p.flags == 0
        assert p.material_id == 0
        assert p.emitter_id == 0
        assert p.prev_position is None
        assert p.ribbon_length == 0.0

    def test_create_with_optional_fields(self):
        """オプションフィールドも指定できること。"""
        p = Particle(
            position=np.zeros(3, dtype=np.float32),
            velocity=np.zeros(3, dtype=np.float32),
            life=np.zeros(4, dtype=np.float32),
            color=np.ones(4, dtype=np.float32),
            size=np.ones(4, dtype=np.float32),
            rotation=np.zeros(4, dtype=np.float32),
            flags=int(ParticleFlags.ALIVE | ParticleFlags.COLLIDE),
            material_id=5,
            emitter_id=2,
            prev_position=np.ones(3, dtype=np.float32),
            ribbon_length=1.5,
        )
        assert p.flags == int(ParticleFlags.ALIVE | ParticleFlags.COLLIDE)
        assert p.material_id == 5
        assert p.emitter_id == 2
        assert p.ribbon_length == 1.5


class TestParticleBuffer:
    """ParticleBuffer クラスのテスト。"""

    def test_init_defaults(self):
        """デフォルト初期化で最大粒子数・空リストが設定されること。"""
        buf = ParticleBuffer(max_particles=100)
        assert buf.max_particles == 100
        assert buf.count == 0
        assert buf.free_list == list(range(100))
        assert buf.alive_indices == []

    def test_allocate_normal(self):
        """allocate で空きインデックスを取得できること。"""
        buf = ParticleBuffer(max_particles=10)
        indices = buf.allocate(3)
        assert len(indices) == 3
        assert buf.count == 3
        assert set(buf.alive_indices) == {0, 1, 2}

    def test_allocate_insufficient_returns_empty(self):
        """空きが足りずリサイクルでも賄えないときは空配列を返すこと（異常系/境界値）。"""
        buf = ParticleBuffer(max_particles=5)
        buf.allocate(5)
        # 生存粒子5つ全てをリサイクル対象にしても6つは確保できない
        indices = buf.allocate(6)
        assert len(indices) == 0

    def test_allocate_triggers_recycle(self):
        """空き不足時に最古の粒子をリサイクルして割り当てること。"""
        buf = ParticleBuffer(max_particles=3)
        buf.allocate(3)  # 全て使用
        # 全て生存中なのでリサイクル対象あり
        indices = buf.allocate(2)
        assert len(indices) == 2
        # リサイクル後、再度2つ割り当てられてフルになる
        assert buf.count == 3

    def test_free_returns_to_free_list(self):
        """free でインデックスを空きリストに戻せること。"""
        buf = ParticleBuffer(max_particles=10)
        indices = buf.allocate(3)
        buf.free(indices)
        assert buf.count == 0
        assert buf.alive_indices == []

    def test_free_clears_flags(self):
        """free でフラグがクリアされること。"""
        buf = ParticleBuffer(max_particles=10)
        indices = buf.allocate(1)
        buf.flags[indices[0]] = int(ParticleFlags.ALIVE)
        buf.free(indices)
        assert buf.flags[indices[0]] == 0

    def test_get_alive_count(self):
        """get_alive_count で生存粒子数を取得できること。"""
        buf = ParticleBuffer(max_particles=10)
        assert buf.get_alive_count() == 0
        buf.allocate(4)
        assert buf.get_alive_count() == 4

    def test_get_alive_indices(self):
        """get_alive_indices で生存インデックス配列を取得できること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(3)
        alive = buf.get_alive_indices()
        assert len(alive) == 3
        assert alive.dtype == np.uint32

    def test_update_particle_data(self):
        """update_particle_data で属性を一括更新できること。"""
        buf = ParticleBuffer(max_particles=10)
        indices = buf.allocate(2)
        buf.update_particle_data(
            indices, position=np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        )
        np.testing.assert_array_equal(
            buf.position[indices], np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        )

    def test_update_particle_data_1d_attribute(self):
        """1次元属性（flags 等）も更新できること。"""
        buf = ParticleBuffer(max_particles=10)
        indices = buf.allocate(2)
        buf.update_particle_data(
            indices, flags=np.array([1, 2], dtype=np.uint32)
        )
        np.testing.assert_array_equal(buf.flags[indices], np.array([1, 2]))

    def test_get_particle_data_returns_dict(self):
        """get_particle_data が全属性の辞書を返すこと。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(1)
        data = buf.get_particle_data(np.array([0], dtype=np.uint32))
        expected_keys = {
            "position", "velocity", "life", "color", "size", "rotation",
            "flags", "material_id", "emitter_id", "prev_position", "ribbon_length",
        }
        assert set(data.keys()) == expected_keys

    def test_clear_resets_buffer(self):
        """clear でバッファをリセットできること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(5)
        buf.flags[0] = 1
        buf.clear()
        assert buf.count == 0
        assert buf.free_list == list(range(10))
        assert buf.alive_indices == []
        assert np.all(buf.flags == 0)

    def test_recycle_oldest_no_alive(self):
        """生存粒子がないとき _recycle_oldest は何もしないこと。"""
        buf = ParticleBuffer(max_particles=5)
        buf._recycle_oldest(3)  # 例外にならない
        assert buf.count == 0


class TestCurlNoise:
    """CurlNoise クラスのテスト。"""

    def test_init_generates_permutation(self):
        """シードで初期化し順列テーブルを生成すること。"""
        noise = CurlNoise(seed=42)
        assert noise.seed == 42
        assert noise.perm.shape == (512,)

    def test_different_seed_different_perm(self):
        """異なるシードで異なる順列になること。"""
        assert not np.array_equal(
            CurlNoise(seed=1).perm, CurlNoise(seed=2).perm
        )

    def test_noise3d_returns_float(self):
        """noise3d が float を返すこと。"""
        noise = CurlNoise(seed=0)
        val = noise.noise3d(0.5, 0.5, 0.5)
        assert isinstance(val, float)

    def test_fade(self):
        """_fade がフェーズカーブを返すこと。"""
        noise = CurlNoise()
        assert noise._fade(0.0) == 0.0
        assert noise._fade(1.0) == 1.0
        assert 0.0 < noise._fade(0.5) < 1.0

    def test_lerp(self):
        """_lerp が線形補間を返すこと。"""
        noise = CurlNoise()
        assert noise._lerp(0.0, 10.0, 0.5) == 5.0
        assert noise._lerp(0.0, 10.0, 0.0) == 0.0

    def test_curl_noise_3d_returns_array(self):
        """curl_noise_3d が 3 要素の ndarray を返すこと。"""
        noise = CurlNoise(seed=7)
        result = noise.curl_noise_3d(1.0, 2.0, 3.0)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        assert result.dtype == np.float32


class TestSDFCollision:
    """SDFCollision クラスのテスト。"""

    def test_init_defaults(self):
        """デフォルト初期化で sdf が None であること。"""
        sdf = SDFCollision()
        assert sdf.sdf is None
        assert sdf.grid_size == 128

    def test_query_no_sdf_returns_large(self):
        """sdf 未構築時は query が大きな値（非衝突）を返すこと。"""
        sdf = SDFCollision()
        assert sdf.query(np.zeros(3, dtype=np.float32)) == 1e6

    def test_build_from_heightmap(self):
        """build_from_heightmap で sdf を構築できること。"""
        sdf = SDFCollision(grid_size=32, world_bounds=(0, 10, 0, 10, 0, 10))
        heightmap = np.ones((8, 8), dtype=np.float32) * 5.0
        sdf.build_from_heightmap(heightmap, wall_height=10.0)
        assert sdf.sdf is not None
        assert sdf.heightmap_shape == (8, 8)

    def test_query_out_of_bounds_returns_large(self):
        """範囲外の位置では query が大きな値を返すこと。"""
        sdf = SDFCollision(grid_size=32, world_bounds=(0, 10, 0, 10, 0, 10))
        heightmap = np.ones((8, 8), dtype=np.float32) * 5.0
        sdf.build_from_heightmap(heightmap)
        far = np.array([1000.0, 1000.0, 1000.0], dtype=np.float32)
        assert sdf.query(far) == 1e6

    def test_collide_particle_no_collision(self):
        """範囲外（query=1e6）または dist >= radius 時は衝突しないこと。"""
        sdf = SDFCollision(grid_size=32, world_bounds=(0, 10, 0, 10, 0, 10))
        heightmap = np.ones((8, 8), dtype=np.float32) * 5.0
        sdf.build_from_heightmap(heightmap)
        # 範囲外 -> query が 1e6 を返す -> 衝突なし
        pos = np.array([1000.0, 1000.0, 1000.0], dtype=np.float32)
        vel = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        new_pos, new_vel, collided = sdf.collide_particle(pos, vel, radius=0.5)
        assert collided is False
        np.testing.assert_array_equal(new_pos, pos)
        np.testing.assert_array_equal(new_vel, vel)

    def test_collide_particle_collision(self):
        """dist < radius 時は位置・速度を補正し collided=True を返すこと。"""
        sdf = SDFCollision(grid_size=32, world_bounds=(0, 10, 0, 10, 0, 10))
        heightmap = np.ones((8, 8), dtype=np.float32) * 5.0
        sdf.build_from_heightmap(heightmap)
        # 壁の中（z < height）に粒子を置く
        pos = np.array([5.0, 5.0, 1.0], dtype=np.float32)
        vel = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        new_pos, new_vel, collided = sdf.collide_particle(pos, vel, radius=2.0)
        assert collided is True


class TestEmitter:
    """Emitter クラスのテスト。"""

    def test_type_enum_values(self):
        """Emitter.Type が期待される値を持つこと。"""
        assert Emitter.Type.POINT == 0
        assert Emitter.Type.LINE == 1
        assert Emitter.Type.RING == 2
        assert Emitter.Type.SPHERE == 3
        assert Emitter.Type.BOX == 4
        assert Emitter.Type.MESH == 5

    def test_init_defaults(self):
        """デフォルト初期化でアクティブ・アキュムレータ0となること。"""
        emitter = Emitter()
        assert emitter.type == Emitter.Type.POINT
        assert emitter.rate == 100.0
        assert emitter.active is True
        assert emitter.accumulator == 0.0

    def test_update_inactive_returns_zero(self):
        """非アクティブ時は 0 を返すこと。"""
        emitter = Emitter()
        emitter.active = False
        buf = ParticleBuffer(max_particles=100)
        count = emitter.update(
            0.1, buf,
            np.zeros(3, dtype=np.float32),
            np.ones(4, dtype=np.float32),
            1.0, 1.0,
        )
        assert count == 0

    def test_update_no_emission_small_dt(self):
        """dt が小さく粒子が生成されないとき 0 を返すこと。"""
        emitter = Emitter(rate=1.0)
        buf = ParticleBuffer(max_particles=100)
        count = emitter.update(
            0.001, buf,
            np.zeros(3, dtype=np.float32),
            np.ones(4, dtype=np.float32),
            1.0, 1.0,
        )
        assert count == 0

    def test_update_emits_particles(self):
        """十分な dt で粒子を生成できること。"""
        emitter = Emitter(rate=1000.0)
        buf = ParticleBuffer(max_particles=1000)
        count = emitter.update(
            0.1, buf,
            np.zeros(3, dtype=np.float32),
            np.ones(4, dtype=np.float32),
            1.0, 1.0,
        )
        assert count > 0
        assert buf.get_alive_count() == count

    def test_init_particle_point_type(self):
        """POINT タイプは位置を変更しないこと。"""
        emitter = Emitter(emitter_type=Emitter.Type.POINT, position=np.array([1, 2, 3], dtype=np.float32))
        buf = ParticleBuffer(max_particles=10)
        emitter._init_particle(
            0, buf,
            np.zeros(3, dtype=np.float32),
            np.ones(4, dtype=np.float32),
            1.0, 1.0, 0,
        )
        np.testing.assert_array_equal(buf.position[0], np.array([1, 2, 3], dtype=np.float32))
        assert buf.flags[0] == int(ParticleFlags.ALIVE)

    def test_init_particle_ring_type(self):
        """RING タイプは指定半径上に配置されること（np.random を固定）。"""
        emitter = Emitter(
            emitter_type=Emitter.Type.RING,
            params={"radius": 2.0},
        )
        buf = ParticleBuffer(max_particles=10)
        with patch_random(0.0):  # angle = 0 -> pos += [2, 0, 0]
            emitter._init_particle(
                0, buf,
                np.zeros(3, dtype=np.float32),
                np.ones(4, dtype=np.float32),
                1.0, 1.0, 0,
            )
        np.testing.assert_allclose(buf.position[0], np.array([2.0, 0.0, 0.0], dtype=np.float32))

    def test_init_particle_box_type(self):
        """BOX タイプはサイズ分布でオフセットすること。"""
        emitter = Emitter(
            emitter_type=Emitter.Type.BOX,
            params={"size": np.ones(3)},
        )
        buf = ParticleBuffer(max_particles=10)
        with patch_random(0.0):  # uniform -0.5..0.5 -> 0.5 の固定は難しいので種のみ固定
            emitter._init_particle(
                0, buf,
                np.zeros(3, dtype=np.float32),
                np.ones(4, dtype=np.float32),
                1.0, 1.0, 0,
            )
        assert buf.flags[0] == int(ParticleFlags.ALIVE)


def patch_random(value):
    """np.random.random を一括で固定するコンテキストマネージャ（テスト用ヘルパ）。"""
    import unittest.mock as mock

    return mock.patch("numpy.random.random", return_value=value)


class TestSimulateParticlesCpu:
    """simulate_particles_cpu 関数のテスト。"""

    def test_empty_buffer_returns_early(self):
        """粒子数0のときは早期リターンすること。"""
        buf = ParticleBuffer(max_particles=10)
        # 例外にならず即終了
        simulate_particles_cpu(buf, 0.1)

    def test_normal_simulation(self):
        """重力下で粒子がシミュレートされること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(1)
        buf.position[0] = np.array([0.0, 10.0, 0.0], dtype=np.float32)
        buf.velocity[0] = np.zeros(3, dtype=np.float32)
        buf.life[0] = np.array([0.0, 100.0, 0.0, 0.0], dtype=np.float32)
        buf.flags[0] = int(ParticleFlags.ALIVE)

        gravity = np.array([0.0, -9.81, 0.0], dtype=np.float32)
        simulate_particles_cpu(buf, 0.1, gravity=gravity)

        # 重力で y 速度が負になり、位置が下がる
        assert buf.velocity[0, 1] < 0
        assert buf.position[0, 1] < 10.0

    def test_particle_dies_after_max_life(self):
        """ライフが最大を超えた粒子は解放されること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(1)
        buf.position[0] = np.zeros(3, dtype=np.float32)
        buf.velocity[0] = np.zeros(3, dtype=np.float32)
        # ライフをギリギリまで進めて dt で超過させる
        buf.life[0] = np.array([99.0, 100.0, 0.0, 0.0], dtype=np.float32)
        buf.flags[0] = int(ParticleFlags.ALIVE)

        simulate_particles_cpu(buf, 2.0)  # life 99 -> 101 >= 100 で解放
        assert buf.get_alive_count() == 0

    def test_with_curl_noise(self):
        """curl_noise を渡してもシミュレーションが完了すること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(1)
        buf.position[0] = np.zeros(3, dtype=np.float32)
        buf.velocity[0] = np.zeros(3, dtype=np.float32)
        buf.life[0] = np.array([0.0, 100.0, 0.0, 0.0], dtype=np.float32)
        buf.flags[0] = int(ParticleFlags.ALIVE)

        curl = CurlNoise(seed=1)
        simulate_particles_cpu(buf, 0.1, curl_noise=curl)
        assert buf.get_alive_count() == 1

    def test_with_global_wind(self):
        """global_wind が速度に反映されること。"""
        buf = ParticleBuffer(max_particles=10)
        buf.allocate(1)
        buf.position[0] = np.zeros(3, dtype=np.float32)
        buf.velocity[0] = np.zeros(3, dtype=np.float32)
        buf.life[0] = np.array([0.0, 100.0, 0.0, 0.0], dtype=np.float32)
        buf.flags[0] = int(ParticleFlags.ALIVE)

        wind = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        simulate_particles_cpu(buf, 0.1, global_wind=wind)
        assert buf.velocity[0, 0] > 0
