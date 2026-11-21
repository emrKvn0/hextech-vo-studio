# -*- coding: utf-8 -*-
"""
================================================================================
Quotes and Subtitles Server Routes (server_routes/quotes_routes.py)
================================================================================
Handles REST API endpoints for League Wiki and SkinSpotlights Quotes/Subtitles.
"""

import os
import sys
import json
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from wiki_voice_pipeline import VOPipeline, WikiAudioFetcher

def handle_quotes_get(handler, path, params, context):
    """
    Handles GET requests for quotes.
    - /api/quotes?champion=Sett&skin=Classic
    - /api/quotes/tabs?champion=Sett
    """
    CHAMPIONS_OUTPUT_PATH = context.get('CHAMPIONS_OUTPUT_PATH', os.path.join(PROJECT_ROOT, "Champions"))

    if path == '/api/quotes/tabs':
        champion = params.get('champion', [''])[0]
        if not champion:
            handler.send_json({"error": "Champion parameter required"})
            return True
        info = WikiAudioFetcher.list_available_sections_and_tabs(champion)
        handler.send_json(info)
        return True

    if path == '/api/quotes':
        champion = params.get('champion', [''])[0]
        skin = params.get('skin', ['Classic'])[0]
        if not champion:
            handler.send_json({"error": "Champion parameter required"})
            return True

        champ_json = os.path.join(CHAMPIONS_OUTPUT_PATH, champion, f"{champion}_voice_quotes.json")
        if os.path.exists(champ_json):
            try:
                with open(champ_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if skin and "skins" in data and skin in data["skins"]:
                    handler.send_json(data["skins"][skin])
                    return True
                handler.send_json(data)
                return True
            except Exception as e:
                handler.send_json({"error": f"JSON okuma hatası: {str(e)}"})
                return True

        handler.send_json({"quotes": [], "message": "Henüz bu şampiyon için replik verisi çekilmemiş"})
        return True

    return False

def handle_quotes_post(handler, path, body, context):
    """
    Handles POST requests for quotes sync.
    - /api/quotes/sync  { "champion": "Sett", "skin": "Classic", "use_whisper": false }
    """
    if path == '/api/quotes/sync':
        champion = body.get('champion', '')
        skin = body.get('skin', 'Classic')
        use_whisper = body.get('use_whisper', False)

        if not champion:
            handler.send_json({"error": "champion parametresi zorunludur"})
            return True

        # Pipeline'ı çalıştır
        try:
            result = VOPipeline.run(
                champion=champion,
                skin_name=skin,
                use_whisper=use_whisper,
                translate=True
            )
            handler.send_json({
                "status": "success",
                "champion": champion,
                "skin": skin,
                "total_quotes": result.get("total_quotes", 0),
                "source": result.get("source_used", ""),
                "match_summary": result.get("match_summary", {}),
                "output_file": result.get("output_file", "")
            })
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)})

        return True

    return False
