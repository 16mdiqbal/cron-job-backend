"""
Allow src to be run as a module: python -m src
"""
from .app import app

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5001, debug=app.config['DEBUG'])
    except (KeyboardInterrupt, SystemExit):
        from .scheduler import scheduler
        # Gracefully shut down scheduler on exit
        if scheduler.running:
            scheduler.shutdown()
        raise
