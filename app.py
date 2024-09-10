import os

from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify, request
from mem0 import Memory
from tenacity import retry, stop_after_attempt, wait_fixed
from neo4j import GraphDatabase, exceptions

load_dotenv()

app = Flask(__name__)

@retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
def connect_to_neo4j():
    url = os.environ.get("NEO4J_URL")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    try:
        driver = GraphDatabase.driver(url, auth=(username, password))
        driver.verify_connectivity()
        driver.close()
    except exceptions.ServiceUnavailable:
        print("Neo4j is not available yet. Retrying...")
        raise

# Attempt to connect to Neo4j before initializing the Memory
connect_to_neo4j()

app.url_map.strict_slashes = False

api = Blueprint("api", __name__, url_prefix="/v1")

config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.2,
            "max_tokens": 1500,
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-large",
            "embedding_dims": 3072,
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": os.environ.get("QDRANT_HOST", "localhost"),
            "port": os.environ.get("QDRANT_PORT", 6333),
            "embedding_model_dims": 3072,
            "on_disk": True,
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": os.environ.get("NEO4J_URL"),
            "username": os.environ.get("NEO4J_USERNAME"),
            "password": os.environ.get("NEO4J_PASSWORD"),
        },
        "llm" : {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.0,
            }
        }
    },
    "version": "v1.1"
}

memory = Memory.from_config(config)


@api.route("/memories", methods=["POST"])
def add_memories():
    try:
        body = request.get_json()
        return memory.add(
            body["messages"],
            user_id=body.get("user_id"),
            agent_id=body.get("agent_id"),
            run_id=body.get("run_id"),
            metadata=body.get("metadata"),
            filters=body.get("filters"),
            prompt=body.get("prompt"),
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@api.route("/memories/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    try:
        existing_memory = memory.get(memory_id)
        if not existing_memory:
            return jsonify({"message": "Memory not found!"}), 400
        body = request.get_json()
        return memory.update(memory_id, data=body["data"])
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@api.route("/memories/search", methods=["POST"])
def search_memories():
    try:
        body = request.get_json()
        return memory.search(
            body["query"],
            user_id=body.get("user_id"),
            agent_id=body.get("agent_id"),
            run_id=body.get("run_id"),
            limit=body.get("limit", 100),
            filters=body.get("filters"),
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 400

@api.route("/memories", methods=["GET"])
def get_memories():
    try:
        return memory.get_all(
            user_id=request.args.get("user_id"),
            agent_id=request.args.get("agent_id"),
            run_id=request.args.get("run_id"),
            limit=request.args.get("limit", 100),
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@api.route("/memories/<memory_id>/history", methods=["GET"])
def get_memory_history(memory_id):
    try:
        return memory.history(memory_id)
    except Exception as e:
        return jsonify({"message": str(e)}), 400


app.register_blueprint(api)
