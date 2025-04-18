"""Generic Agent entrypoint. Role determined by $AGENT_ROLE."""
import json, os, time, uuid
from confluent_kafka import Consumer, Producer
from crewai import Agent, Task

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
ROLE = os.getenv("AGENT_ROLE", "developer")
TOPIC_IN = {
    "product_manager": "product-requirements",
    "ux_researcher": "ux-findings",
    "project_manager": "project-tasks",
    "developer": "dev-tasks",
    "debugger": "debug-requests",
    "code_reviewer": "review-requests",
    "tester": "test-plan-requests",
    "frontend_tester": "ui-test-jobs",
    "performance_tester": "perf-jobs",
    "security_auditor": "sec-alerts",
    "tech_writer": "docs",
    "devops_bot": "ops-tasks",
    "release_manager": "release-orders",
}.get(ROLE, "general")

TOPIC_OUT = {
    "product_manager": "project-tasks",
    "ux_researcher": "ux-findings",
    "project_manager": "dev-tasks",
    "developer": "code-artifacts",
    "debugger": "dev-tasks",
    "code_reviewer": "review-results",
    "tester": "ui-test-jobs",
    "frontend_tester": "test-results",
    "performance_tester": "perf-results",
    "security_auditor": "sec-alerts",
    "tech_writer": "docs",
    "devops_bot": "ops-results",
    "release_manager": "release-orders",
}.get(ROLE, "general")

producer = Producer({"bootstrap.servers": BOOTSTRAP})
consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": f"{ROLE}-group",
    "auto.offset.reset": "earliest"
})
consumer.subscribe([TOPIC_IN])

agent = Agent(name=ROLE.replace("_", " ").title())

print(f"🚀 {ROLE} ready | in={TOPIC_IN} out={TOPIC_OUT}")
while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    try:
        body = json.loads(msg.value())
    except Exception:
        continue
    task_text = body.get("idea") or body.get("summary") or str(body)
    task = Task(description=task_text)
    result = agent.run(task)
    out_msg = json.dumps({"id": str(uuid.uuid4()), "sender": ROLE,
                          "recipient": "", "result": result})
    producer.produce(TOPIC_OUT, out_msg.encode())
    producer.flush()
    consumer.commit(msg) 