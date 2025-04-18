"""Bootstraps the whole self‑coding stack and keeps it healthy.
Run:  python orchestrator.py --idea "todo‑list webapp"
"""
import argparse, json, os, signal, sys, time, threading, uuid
from pathlib import Path
from typing import Dict, List

import docker  # pip install docker
from confluent_kafka.admin import AdminClient  # pip install confluent-kafka

NETWORK = "selfcoder_net"
AGENT_IMAGE = "selfcoder/agent-base:latest"
DASHBOARD_IMAGE = "selfcoder/dashboard:latest"
IDEA_TOPIC = "product-requirements"
ROLES = [
    "product_manager", "ux_researcher", "project_manager", "release_manager",
    "developer", "debugger", "code_reviewer", "tester", "frontend_tester",
    "performance_tester", "security_auditor", "tech_writer", "devops_bot"
]

class Orchestrator:
    def __init__(self, idea: str):
        self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        self.idea = idea
        self.kafka_bootstrap = "kafka:9092"
        self._ensure_network()
        self._start_infra()
        self._build_images()
        self._start_dashboard()
        self._seed_idea()
        self._start_agents()
        self._monitor_loop()

    # ----- infra helpers --------------------------------------------------
    def _ensure_network(self):
        try:
            self.client.networks.get(NETWORK)
        except docker.errors.NotFound:
            self.client.networks.create(NETWORK, driver="bridge")
        print("✔ docker network", NETWORK)

    def _run(self, **kwargs):
        kwargs.setdefault("network", NETWORK)
        kwargs.setdefault("detach", True)
        
        # Convert env dict to a list of "key=value" strings if present
        if 'env' in kwargs and isinstance(kwargs['env'], dict):
            env_dict = kwargs.pop('env')
            env_list = [f"{k}={v}" for k, v in env_dict.items()]
            kwargs['environment'] = env_list
            
        return self.client.containers.run(**kwargs)

    def _start_infra(self):
        """ZooKeeper ➜ Kafka ➜ Postgres ➜ MinIO ➜ Gitea ➜ Drone ➜ Ollama"""
        infra = [
            dict(image="bitnami/zookeeper:latest", name="zookeeper"),
            dict(image="bitnami/kafka:latest", name="kafka", env={
                "KAFKA_CFG_ZOOKEEPER_CONNECT": "zookeeper:2181",
                "ALLOW_PLAINTEXT_LISTENER": "yes",
                "KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP": "INTERNAL:PLAINTEXT",
                "KAFKA_CFG_LISTENERS": "INTERNAL://:9092",
                "KAFKA_CFG_ADVERTISED_LISTENERS": "INTERNAL://kafka:9092",
                "KAFKA_INTER_BROKER_LISTENER_NAME": "INTERNAL"
            }),
            dict(image="postgres:16-alpine", name="postgres", env={
                "POSTGRES_PASSWORD": "postgres",
                "POSTGRES_USER": "postgres"
            }, volumes={"pgdata": {"bind": "/var/lib/postgresql/data", "mode": "rw"}}),
            dict(image="minio/minio:latest", name="minio", command="server /data", env={
                "MINIO_ROOT_USER": "minio",
                "MINIO_ROOT_PASSWORD": "minio123"
            }, ports={"9000/tcp": 9000}, volumes={"minio-data": {"bind": "/data", "mode": "rw"}}),
            dict(image="gitea/gitea:1", name="gitea", ports={"3000/tcp": 3000}, volumes={
                "gitea-data": {"bind": "/data", "mode": "rw"}
            }),
            dict(image="drone/drone:2", name="drone", env={
                "DRONE_GITEA_SERVER": "http://gitea:3000",
                "DRONE_RPC_SECRET": "mysecret",
                "DRONE_SERVER_HOST": "drone",
                "DRONE_SERVER_PROTO": "http"
            }, ports={"8080/tcp": 8080}),
            dict(image="ollama/ollama:latest", name="ollama", ports={"11434/tcp": 11434},
                 volumes={"ollama-models": {"bind": "/root/.ollama", "mode": "rw"}})
        ]
        for spec in infra:
            try:
                self.client.containers.get(spec["name"])
                print("⏩", spec["name"], "already running")
            except docker.errors.NotFound:
                self._run(**spec)
                print("▶ started", spec["name"])

    def _build_images(self):
        print("Building agent base image...")
        base_path = Path(__file__).parent / "agents" / "base"
        try:
            output = self.client.images.build(path=str(base_path), tag=AGENT_IMAGE, rm=True, pull=True)
            for line in output[1]:
                if 'stream' in line:
                    print(line['stream'].strip())
        except Exception as e:
            print(f"Error building agent image: {e}")
            raise
            
        print("Building dashboard image...")
        dash_path = Path(__file__).parent / "dashboard"
        try:
            output = self.client.images.build(path=str(dash_path), tag=DASHBOARD_IMAGE, rm=True)
            for line in output[1]:
                if 'stream' in line:
                    print(line['stream'].strip())
        except Exception as e:
            print(f"Error building dashboard image: {e}")
            raise
            
        print("✔ images built")
        
    def _start_dashboard(self):
        try:
            self.client.containers.get("dashboard")
            print("⏩ dashboard already running")
        except docker.errors.NotFound:
            self._run(image=DASHBOARD_IMAGE, name="dashboard", ports={"5000/tcp": 5000})
            print("▶ started dashboard")

    # ----- idea seeding & agents -----------------------------------------
    def _seed_idea(self):
        from confluent_kafka import Producer
        producer = Producer({"bootstrap.servers": self.kafka_bootstrap})
        payload = json.dumps({"id": str(uuid.uuid4()), "idea": self.idea}).encode()
        producer.produce(IDEA_TOPIC, payload)
        producer.flush()
        print("💡 seeded initial idea to", IDEA_TOPIC)

    def _start_agents(self):
        for role in ROLES:
            self._spawn_agent(role)
        print("✔ all agents online")

    def _spawn_agent(self, role: str):
        container_name = f"agent_{role}_1"
        try:
            self.client.containers.get(container_name)
            return  # already exists
        except docker.errors.NotFound:
            pass
        self._run(image=AGENT_IMAGE, name=container_name, environment=[
            f"AGENT_ROLE={role}", f"KAFKA_BOOTSTRAP={self.kafka_bootstrap}"
        ])

    # ----- monitoring -----------------------------------------------------
    def _monitor_loop(self):
        admin = AdminClient({"bootstrap.servers": self.kafka_bootstrap})

        def monitor():
            while True:
                try:
                    lag_info: Dict[str, int] = {}
                    for role in ROLES:
                        group = f"{role}-group"
                        try:
                            m = admin.list_consumer_groups().groups
                            # lag calc omitted for brevity
                        except Exception:
                            pass
                        # SCALE LOGIC EXAMPLE (dummy: spawn second replica if lag>5)
                        if lag_info.get(role, 0) > 5:
                            replica = len([c for c in self.client.containers.list()
                                           if c.name.startswith(f"agent_{role}")]) + 1
                            self._run(image=AGENT_IMAGE,
                                      name=f"agent_{role}_{replica}",
                                      environment=[
                                          f"AGENT_ROLE={role}",
                                          f"KAFKA_BOOTSTRAP={self.kafka_bootstrap}"
                                      ])
                    time.sleep(30)
                except Exception as e:
                    print("Monitor error:", e)
                    time.sleep(30)
        threading.Thread(target=monitor, daemon=True).start()
        print("📡 monitor thread active")
        signal.pause()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", required=True)
    
    def cleanup_containers():
        """Stop and remove all containers in case of failure."""
        print("⚠️ Cleaning up containers due to error...")
        try:
            client = docker.from_env()
            # Get all running containers in our network
            containers = client.containers.list(all=True)
            for container in containers:
                if container.name.startswith("agent_") or container.name == "dashboard":
                    print(f"Stopping container: {container.name}")
                    try:
                        container.stop(timeout=5)
                    except Exception as e:
                        print(f"Error stopping {container.name}: {e}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    try:
        Orchestrator(parser.parse_args().idea)
    except KeyboardInterrupt:
        print("\n⚠️ Orchestrator interrupted by user.")
        cleanup_containers()
    except Exception as e:
        print(f"\n⚠️ Orchestrator failed: {e}")
        cleanup_containers()
        raise 