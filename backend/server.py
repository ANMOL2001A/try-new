import os
import uuid
import logging
from livekit import api
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from livekit.api import LiveKitAPI, ListRoomsRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Validate environment variables
required_env_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    raise ValueError(f"Missing required environment variables: {missing_vars}")

async def generate_room_name():
    """Generate a unique room name"""
    try:
        name = "auto-service-" + str(uuid.uuid4())[:8]
        rooms = await get_rooms()
        
        # Ensure uniqueness
        while name in rooms:
            name = "auto-service-" + str(uuid.uuid4())[:8]
            
        logger.info(f"Generated room name: {name}")
        return name
    except Exception as e:
        logger.error(f"Error generating room name: {e}")
        # Fallback to simple UUID if room listing fails
        return "auto-service-" + str(uuid.uuid4())[:8]

async def get_rooms():
    """Get list of existing rooms"""
    try:
        lk_api = LiveKitAPI(
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
            url=os.getenv("LIVEKIT_URL")
        )
        
        rooms = await lk_api.room.list_rooms(ListRoomsRequest())
        await lk_api.aclose()
        
        room_names = [room.name for room in rooms.rooms]
        logger.info(f"Found {len(room_names)} existing rooms")
        return room_names
        
    except Exception as e:
        logger.error(f"Error fetching rooms: {e}")
        return []

@app.route("/getToken")
async def get_token():
    """Generate LiveKit access token for client"""
    try:
        # Get parameters
        name = request.args.get("name", f"customer-{uuid.uuid4().hex[:6]}")
        room = request.args.get("room", None)
        
        # Generate room if not provided
        if not room:
            room = await generate_room_name()
            
        logger.info(f"Generating token for user: {name}, room: {room}")
        
        # Create access token
        token = api.AccessToken(
            api_key=os.getenv("LIVEKIT_API_KEY"), 
            api_secret=os.getenv("LIVEKIT_API_SECRET")
        ) \
        .with_identity(name) \
        .with_name(name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        ))
        
        jwt_token = token.to_jwt()
        
        response = {
            "token": jwt_token,
            "room": room,
            "user": name,
            "url": os.getenv("LIVEKIT_URL")
        }
        
        logger.info(f"Token generated successfully for room: {room}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({"error": "Failed to generate token"}), 500

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "LiveKit AI Car Call Centre",
        "version": "1.0.0"
    })

@app.route("/rooms")
async def list_rooms():
    """List all active rooms (for debugging)"""
    try:
        rooms = await get_rooms()
        return jsonify({
            "rooms": rooms,
            "count": len(rooms)
        })
    except Exception as e:
        logger.error(f"Error listing rooms: {e}")
        return jsonify({"error": "Failed to list rooms"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting LiveKit AI Car Call Centre server...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    
    app.run(
        host="0.0.0.0", 
        port=5001, 
        debug=True,
        use_reloader=False  # Prevent double initialization in debug mode
    )