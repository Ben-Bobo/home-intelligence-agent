import json
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from app.agent.graph import agent
from app.routes.ask import extract_actions


def run_evals():
    with open("evals/dataset.json") as f:
        dataset = json.load(f)

    results = {
        "tool_selection": {"correct": 0, "total": 0},
        "answer_relevance": {"correct": 0, "total": 0},
        "action_correctness": {"correct": 0, "total": 0}
    }

    passed = 0
    failed = 0

    for item in dataset:
        print(f"\n{'='*60}")
        print(f"Eval {item['id']}: {item['question'][:60]}...")

        thread_id = str(uuid.uuid4())
        human_message = HumanMessage(content=[{"type": "text", "text": item["question"]}])

        initial_state = {
            "question": item["question"],
            "image": None,
            "thread_id": thread_id,
            "messages": [human_message],
            "actions": [],
            "answer": "",
            "error": None
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = agent.invoke(initial_state, config=config)
            messages = result["messages"]
            last_message = messages[-1]
            answer = last_message.content if last_message.content else ""

            # Check tool selection
            tools_called = []
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for call in msg.tool_calls:
                        tools_called.append(call["name"])

            expected_tool = item["expected_tool"]
            tool_correct = expected_tool in tools_called
            results["tool_selection"]["total"] += 1
            if tool_correct:
                results["tool_selection"]["correct"] += 1

            # Check answer relevance
            expected_keywords = item.get("expected_keywords_in_answer", [])
            answer_lower = answer.lower()
            keyword_hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
            keyword_score = keyword_hits / len(expected_keywords) if expected_keywords else 1.0
            answer_relevant = keyword_score >= 0.5
            results["answer_relevance"]["total"] += 1
            if answer_relevant:
                results["answer_relevance"]["correct"] += 1

            # Check action correctness
            if item.get("expected_action"):
                actions = extract_actions(messages)
                has_action = len(actions) > 0
                correct_type = any(
                    a["type"] == item.get("expected_action_type") for a in actions
                ) if has_action else False

                action_correct = has_action and correct_type
                results["action_correctness"]["total"] += 1
                if action_correct:
                    results["action_correctness"]["correct"] += 1
            else:
                actions = extract_actions(messages)
                no_unwanted_action = len(actions) == 0
                results["action_correctness"]["total"] += 1
                if no_unwanted_action:
                    results["action_correctness"]["correct"] += 1

            # Overall pass/fail
            eval_pass = tool_correct and answer_relevant
            if item.get("expected_action"):
                eval_pass = eval_pass and action_correct
            else:
                eval_pass = eval_pass and no_unwanted_action

            if eval_pass:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            print(f"  {status}")
            print(f"  Tool: expected={expected_tool} | called={tools_called} | {'OK' if tool_correct else 'WRONG'}")
            print(f"  Keywords: {keyword_score:.0%} | {'OK' if answer_relevant else 'LOW'}")
            if item.get("expected_action"):
                print(f"  Action: expected={item['expected_action_type']} | got={[a['type'] for a in actions]} | {'OK' if action_correct else 'WRONG'}")
            else:
                print(f"  Action: expected=none | got={[a['type'] for a in actions]} | {'OK' if no_unwanted_action else 'UNWANTED'}")
            print(f"  Answer preview: {answer[:120]}...")

        except Exception as e:
            failed += 1
            print(f"  ERROR: {str(e)}")

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Overall: {passed} passed, {failed} failed out of {len(dataset)}")
    print(f"Pass rate: {passed/len(dataset):.0%}")
    print()

    for metric, counts in results.items():
        rate = counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        print(f"  {metric}: {counts['correct']}/{counts['total']} ({rate:.0%})")

    print()
    if failed > 0:
        print("EVAL FAILED")
        sys.exit(1)
    else:
        print("ALL EVALS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    run_evals()