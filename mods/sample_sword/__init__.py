from mod_loader import mod_loader

def init_mod():
    mod_loader.register_item("sample_sword", {
        "name": "Sample Mod Sword",
        "category": "weapon",
        "char": "/",
        "color": (200, 200, 255),
        "base_weight": 1.5,
        "base_value": 500,
        "dice_num": 2,
        "dice_side": 8,
        "hit_bonus": 5,
        "dmg_bonus": 2
    })

init_mod()
