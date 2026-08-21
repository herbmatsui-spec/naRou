from mod_loader import mod_loader

def on_move_event(data):
    # Just a sample hook
    pass

def init_mod():
    mod_loader.register_event_listener("EVENT_ON_MOVE", on_move_event)

init_mod()
