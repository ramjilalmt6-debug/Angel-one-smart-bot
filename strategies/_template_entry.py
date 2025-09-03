def tick(api=None, live=False):
    try:
        import json, time
        print(json.dumps({"event":"strategy_tick","live":bool(live),"ts":int(time.time())}), flush=True)
    except Exception:
        pass
