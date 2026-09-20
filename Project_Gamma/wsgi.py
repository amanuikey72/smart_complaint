"""
wsgi.py - WSGI entrypoint for production / Vercel deployment.
"""

from app import app

if __name__ == '__main__':
    app.run()
