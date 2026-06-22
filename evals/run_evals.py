import json
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.agent.graph import agent
from app.routes.ask import extract_actions
from app.config import get_settings


def llm_judge(question: str, answer: str, actions_taken: list = None, reference_answer: str = None) -> dict:
    """Use an LLM to score the answer quality."""
    settings = get_settings()
    judge = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout
    )

    action_context = ""
    if actions_taken:
        action_context = f"\nActions the assistant successfully queued: {json.dumps(actions_taken)}\nThese actions were executed by the system. The assistant does not need to explain the mechanism."

    reference_context = ""
    groundedness_criteria = "groundedness: Does the answer make specific claims rather than vague generalities?"
    if reference_answer:
        reference_context = f"\n\nKNOWN CORRECT ANSWER: {reference_answer}"
        groundedness_criteria = "groundedness: Does the answer match the known correct answer above? If the assistant states a different fact than the known correct answer, score 0. This is the most important criteria."

    prompt = f"""You are evaluating an AI assistant's response. Score the following.

    Question: {question}{reference_context}

    Assistant's Answer: {answer}{action_context}

    Score each criteria from 0 to 1:
    1. relevance: Does the answer actually address the question asked?
    2. {groundedness_criteria}
    3. completeness: Does the answer fully address the question or is it partial?

    If the assistant was asked to perform an action (add to calendar, create a task, etc) and the action was successfully queued, score completeness based on whether the action was appropriate, not on whether the answer explains the technical mechanism.

    Respond with ONLY a JSON object, no other text:
    {{"relevance": 0.0, "groundedness": 0.0, "completeness": 0.0, "reasoning": "brief explanation"}}"""

    try:
        response = judge.invoke(prompt)
        text = response.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        scores = json.loads(text)
        return scores
    except Exception as e:
        print(f"  Judge failed: {str(e)}")
        return {"relevance": 0.0, "groundedness": 0.0, "completeness": 0.0, "reasoning": "judge error"}


def run_evals():
    with open("evals/dataset.json") as f:
        dataset = json.load(f)

    results = {
        "tool_selection": {"correct": 0, "total": 0},
        "answer_quality": {"scores": []},
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

            # LLM-as-judge for answer quality
            actions = extract_actions(messages)
            judge_scores = llm_judge(item["question"], answer, actions_taken=actions, reference_answer=item.get("reference_answer"))
            
            relevance = judge_scores.get("relevance", 0)
            groundedness = judge_scores.get("groundedness", 0)
            completeness = judge_scores.get("completeness", 0)
            avg_quality = (relevance + groundedness + completeness) / 3
            
            results["answer_quality"]["scores"].append(avg_quality)
            
            MIN_SCORE = 0.3
            answer_good = avg_quality >= 0.6 and relevance >= MIN_SCORE and groundedness >= MIN_SCORE and completeness >= MIN_SCORE

            # Check action correctness
            actions = extract_actions(messages)
            if item.get("expected_action"):
                has_action = len(actions) > 0
                expected_types = item.get("expected_action_type")
                if isinstance(expected_types, str):
                    expected_types = [expected_types]
                correct_type = any(
                    a["type"] in expected_types for a in actions
                ) if has_action else False

                action_correct = has_action and correct_type
                results["action_correctness"]["total"] += 1
                if action_correct:
                    results["action_correctness"]["correct"] += 1
            else:
                no_unwanted_action = len(actions) == 0
                action_correct = no_unwanted_action
                results["action_correctness"]["total"] += 1
                if no_unwanted_action:
                    results["action_correctness"]["correct"] += 1

            # Overall pass/fail
            eval_pass = tool_correct and answer_good and action_correct

            if eval_pass:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            print(f"  {status}")
            print(f"  Tool: expected={expected_tool} | called={tools_called} | {'OK' if tool_correct else 'WRONG'}")
            print(f"  Quality: relevance={judge_scores.get('relevance', 0):.1f} "
                  f"groundedness={judge_scores.get('groundedness', 0):.1f} "
                  f"completeness={judge_scores.get('completeness', 0):.1f} "
                  f"avg={avg_quality:.2f} | {'OK' if answer_good else 'LOW'}")
            print(f"  Judge reasoning: {judge_scores.get('reasoning', 'n/a')}")
            if item.get("expected_action"):
                print(f"  Action: expected={item['expected_action_type']} | got={[a['type'] for a in actions]} | {'OK' if action_correct else 'WRONG'}")
            else:
                print(f"  Action: expected=none | got={[a['type'] for a in actions]} | {'OK' if action_correct else 'UNWANTED'}")
            print(f"  Answer preview: {answer[:120]}...")

        except Exception as e:
            failed += 1
            print(f"  ERROR: {str(e)}")

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")

    pass_rate = passed / len(dataset)
    print(f"Overall: {passed} passed, {failed} failed out of {len(dataset)}")
    print(f"Pass rate: {pass_rate:.0%}")
    print()

    tool_total = results["tool_selection"]["total"]
    tool_correct = results["tool_selection"]["correct"]
    tool_rate = tool_correct / tool_total if tool_total > 0 else 0
    print(f"  tool_selection: {tool_correct}/{tool_total} ({tool_rate:.0%})")

    quality_scores = results["answer_quality"]["scores"]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    print(f"  answer_quality: avg={avg_quality:.2f}")

    action_total = results["action_correctness"]["total"]
    action_correct = results["action_correctness"]["correct"]
    action_rate = action_correct / action_total if action_total > 0 else 0
    print(f"  action_correctness: {action_correct}/{action_total} ({action_rate:.0%})")

    # Thresholds
    PASS_RATE_THRESHOLD = 0.8
    TOOL_THRESHOLD = 0.9
    ACTION_THRESHOLD = 0.9

    print()
    all_passed = True
    if pass_rate < PASS_RATE_THRESHOLD:
        print(f"FAIL: Overall pass rate {pass_rate:.0%} below threshold {PASS_RATE_THRESHOLD:.0%}")
        all_passed = False
    if tool_rate < TOOL_THRESHOLD:
        print(f"FAIL: Tool selection {tool_rate:.0%} below threshold {TOOL_THRESHOLD:.0%}")
        all_passed = False
    if action_rate < ACTION_THRESHOLD:
        print(f"FAIL: Action correctness {action_rate:.0%} below threshold {ACTION_THRESHOLD:.0%}")
        all_passed = False

    if all_passed:
        print("ALL THRESHOLDS MET")
        sys.exit(0)
    else:
        print("EVAL FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run_evals()