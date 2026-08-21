from event_bus import event_bus, EVENT_BEFORE_DAMAGE

def on_before_damage(data):
    """
    Step 13: 星座共鳴パッシブをイベントフックへリファクタリング
    Void-Flame resonance check.
    """
    attacker = data.get("attacker")
    if not attacker:
        return
        
    # Check if attacker has the Void-Flame resonance passive
    if hasattr(attacker, "resonances") and "Void-Flame" in attacker.resonances:
        # +150% damage
        original_damage = data["damage"]
        data["damage"] = int(original_damage * 2.5)

def on_move_toxicity(data):
    """
    Step 15: 毒性（Toxicity）の歩行時ダメージ処理をEVENT_ON_MOVEでリスナー処理。
    """
    entity = data.get("entity")
    if not entity:
        return
    
    # If entity is overloaded with toxicity, take 1 damage per step
    if hasattr(entity, "toxicity_state") and getattr(entity.toxicity_state, "is_overloaded", False):
        entity.hp -= 1
        # Check if we should log it or if event_bus can access logger

def register_hooks():
    from event_bus import event_bus, EVENT_ON_MOVE
    event_bus.subscribe(EVENT_BEFORE_DAMAGE, on_before_damage)
    event_bus.subscribe(EVENT_ON_MOVE, on_move_toxicity)
