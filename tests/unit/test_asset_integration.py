"""Tests for asset manager integration with tiny rogue, audio, and emote packs."""

import unittest
import yaml
from asset_manager import ASSET_MANAGER
from emote_system import EMOTE_SYSTEM, play_emote, get_emote_frame


class TestAssetManagerIntegration(unittest.TestCase):
    """Test asset manager loads all asset packs correctly."""
    
    @classmethod
    def setUpClass(cls):
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
        ASSET_MANAGER.initialize(config)
    
    def test_tiny_rogue_tiles_loaded(self):
        """Test that all 132 tiny rogue tiles are loaded."""
        tiles = ASSET_MANAGER.list_tiny_rogue_tiles()
        self.assertEqual(len(tiles), 132)
        # Check a few known tiles
        self.assertIn("tile_0000", tiles)
        self.assertIn("tile_0068", tiles)
        self.assertIn("tile_0131", tiles)
    
    def test_tiny_rogue_atlas_meta_loaded(self):
        """Test that atlas metadata is loaded."""
        meta = ASSET_MANAGER.get_tiny_rogue_atlas_meta()
        self.assertIsNotNone(meta)
        self.assertIn("tiles", meta)
        self.assertEqual(meta["tile_size"], 16)
    
    def test_tile_atlas_info_lookup(self):
        """Test looking up tile atlas coordinates."""
        info = ASSET_MANAGER.get_tile_atlas_info("TR_FLOOR_01")
        self.assertIsNotNone(info)
        self.assertEqual(info["x"], 0)
        self.assertEqual(info["y"], 0)
        self.assertEqual(info["width"], 16)
        self.assertEqual(info["height"], 16)
        
        # Test directional tile (monster)
        info = ASSET_MANAGER.get_tile_atlas_info("TR_MONSTER_01")
        self.assertIsNotNone(info)
        self.assertTrue(info["animated"])
        self.assertEqual(info["directions"], 4)
        self.assertEqual(info["frames"], 4)
    
    def test_audio_sfx_loaded(self):
        """Test that audio SFX files are loaded."""
        sfx = ASSET_MANAGER.list_audio_sfx()
        self.assertEqual(len(sfx), 51)
        self.assertIn("footstep00", sfx)
        self.assertIn("doorOpen_1", sfx)
        self.assertIn("metalPot3", sfx)
    
    def test_audio_manifest_loaded(self):
        """Test that audio manifest is parsed."""
        manifest = ASSET_MANAGER.get_audio_manifest()
        self.assertIsNotNone(manifest)
        self.assertEqual(len(manifest), 51)
        # Check a manifest entry
        entry = manifest[0]
        self.assertIn("filename", entry)
        self.assertIn("category", entry)
        self.assertIn("suggested_id", entry)
    
    def test_audio_lookup_by_suggested_id(self):
        """Test looking up audio by suggested_id."""
        path = ASSET_MANAGER.get_audio_sfx_by_id("se_footstep_00")
        self.assertIsNotNone(path)
        self.assertTrue(path.endswith("footstep00.ogg"))
        
        path = ASSET_MANAGER.get_audio_sfx_by_id("se_door_open_1")
        self.assertIsNotNone(path)
        self.assertTrue(path.endswith("doorOpen_1.ogg"))
    
    def test_emote_sprites_loaded(self):
        """Test that emote sprites are loaded."""
        sprites = ASSET_MANAGER.list_emote_sprites()
        self.assertGreater(len(sprites), 200)
        # Check pixel style1 emotes
        self.assertIn("style1/emote_anger", sprites)
        self.assertIn("style1/emote_heart", sprites)
        # Check tilesheets
        self.assertIn("pixel_style1", sprites)
    
    def test_emote_sprite_lookup(self):
        """Test looking up emote sprite paths."""
        path = ASSET_MANAGER.get_emote_sprite_path("style1/emote_anger")
        self.assertIsNotNone(path)
        self.assertTrue(path.endswith("emote_anger.png"))
        
        path = ASSET_MANAGER.get_emote_tilesheet_path("pixel_style1")
        self.assertIsNotNone(path)
        self.assertTrue(path.endswith("pixel_style1.png"))


class TestEmoteSystem(unittest.TestCase):
    """Test emote system functionality."""
    
    @classmethod
    def setUpClass(cls):
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
        ASSET_MANAGER.initialize(config)
    
    def setUp(self):
        # Reset emote system for each test
        EMOTE_SYSTEM.entity_states.clear()
    
    def test_available_emotes(self):
        """Test that emote definitions are loaded."""
        emotes = EMOTE_SYSTEM.get_available_emotes()
        self.assertGreater(len(emotes), 10)
        self.assertIn("anger", emotes)
        self.assertIn("heart", emotes)
        self.assertIn("sleep", emotes)
    
    def test_play_emote(self):
        """Test playing an emote."""
        result = play_emote("entity1", "anger")
        self.assertTrue(result)
        self.assertTrue(EMOTE_SYSTEM.is_playing("entity1"))
        
        frame = get_emote_frame("entity1")
        self.assertIsNotNone(frame)
        self.assertTrue(frame.endswith("emote_anger.png"))
    
    def test_play_unknown_emote(self):
        """Test playing unknown emote returns False."""
        result = play_emote("entity1", "nonexistent_emote")
        self.assertFalse(result)
        self.assertFalse(EMOTE_SYSTEM.is_playing("entity1"))
    
    def test_stop_emote(self):
        """Test stopping an emote."""
        play_emote("entity1", "heart")
        self.assertTrue(EMOTE_SYSTEM.is_playing("entity1"))
        
        from emote_system import stop_emote
        stop_emote("entity1")
        self.assertFalse(EMOTE_SYSTEM.is_playing("entity1"))
    
    def test_multiple_entities(self):
        """Test multiple entities can play different emotes."""
        play_emote("entity1", "anger")
        play_emote("entity2", "heart")
        play_emote("entity3", "question")
        
        self.assertTrue(EMOTE_SYSTEM.is_playing("entity1"))
        self.assertTrue(EMOTE_SYSTEM.is_playing("entity2"))
        self.assertTrue(EMOTE_SYSTEM.is_playing("entity3"))
        
        frame1 = get_emote_frame("entity1")
        frame2 = get_emote_frame("entity2")
        frame3 = get_emote_frame("entity3")
        
        self.assertTrue(frame1.endswith("emote_anger.png"))
        self.assertTrue(frame2.endswith("emote_heart.png"))
        self.assertTrue(frame3.endswith("emote_question.png"))
    
    def test_sleep_emote_loop(self):
        """Test that sleep emote is marked as looping."""
        # Check the animation definition
        anim = EMOTE_SYSTEM._animation_cache.get("sleep")
        self.assertIsNotNone(anim)
        self.assertTrue(anim.loop)


class TestConfigAssetsSection(unittest.TestCase):
    """Test config.yaml assets section."""
    
    def test_assets_section_exists(self):
        """Test that config.yaml has assets section."""
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
        
        self.assertIn("assets", config)
        assets = config["assets"]
        self.assertIn("tiny_rogue_tiles", assets)
        self.assertIn("tiny_rogue_atlas", assets)
        self.assertIn("tiny_rogue_atlas_meta", assets)
        self.assertIn("audio_sfx", assets)
        self.assertIn("audio_manifest", assets)
        self.assertIn("emote_pixel", assets)
        self.assertIn("emote_tilesheets", assets)
        self.assertIn("emote_spritesheets", assets)


if __name__ == "__main__":
    unittest.main()