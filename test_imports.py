import sys
sys.path.insert(0, '.')
try:
    import naRou.skill_eater.black_market.models
    import naRou.skill_eater.black_market.logic
    import naRou.skill_eater.black_market.ui
    import naRou.skill_eater.facility.models
    import naRou.skill_eater.facility.logic
    import naRou.skill_eater.facility.ui
    print("All imports succeeded")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
