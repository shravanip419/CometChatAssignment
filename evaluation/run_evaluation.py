import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.agent.agent import SupportAgent
from app.models.schemas import AgentResponse


def evaluate_case(case: Dict[str, Any], agent: SupportAgent) -> Tuple[bool, List[str]]:
    """
    Runs an evaluation test case and verifies all assertions.
    Returns (passed, list_of_failure_reasons).
    """
    case_id = case.get("id", "unknown")
    messages = case.get("messages", [])
    expect = case.get("expect", {})
    session_id = f"eval_{case_id}"
    
    last_response: AgentResponse = None
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            last_response = agent.process_message(content, session_id=session_id)
            
    if last_response is None:
        return False, ["No response generated."]

    failures: List[str] = []
    answer = last_response.answer
    ans_lower = answer.lower()
    sources = [s.filename for s in last_response.sources]

    # 1. must_include
    for term in expect.get("must_include", []):
        if term.lower() not in ans_lower:
            failures.append(f"Missing required text: '{term}'")

    # 2. must_not_include
    for term in expect.get("must_not_include", []):
        if term.lower() in ans_lower:
            failures.append(f"Contains forbidden text: '{term}'")

    # 3. must_include_concepts
    for concept in expect.get("must_include_concepts", []):
        c_lower = concept.lower()
        # Evaluate concept keywords
        if "30 days" in c_lower and ("30" not in ans_lower or "day" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "final sale does not block" in c_lower and "final" not in ans_lower:
            failures.append(f"Missing concept: '{concept}'")
        elif "report within 7 days" in c_lower and ("7" not in ans_lower and "seven" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "canada is supported" in c_lower and "canada" not in ans_lower:
            failures.append(f"Missing concept: '{concept}'")
        elif "5–9 business days" in c_lower and ("5–9" not in answer and "5-9" not in answer and "5 to 9" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "duties or taxes" in c_lower and ("duties" not in ans_lower and "taxes" not in ans_lower and "duty" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "germany is not currently available" in c_lower and ("not" not in ans_lower and "available" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "cancelled" in c_lower and "cancelled" not in ans_lower:
            failures.append(f"Missing concept: '{concept}'")
        elif "not found" in c_lower and "not found" not in ans_lower:
            failures.append(f"Missing concept: '{concept}'")
        elif "unavailable" in c_lower and ("unavailable" not in ans_lower and "not" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "no lifetime warranty" in c_lower and ("not" not in ans_lower and "no lifetime" not in ans_lower and "does not offer" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")
        elif "conflict" in c_lower and "conflict" not in ans_lower:
            failures.append(f"Missing concept: '{concept}'")
        elif "insufficient" in c_lower and ("insufficient" not in ans_lower and "does not contain" not in ans_lower):
            failures.append(f"Missing concept: '{concept}'")

    # 4. must_ask_for
    for item in expect.get("must_ask_for", []):
        if item.lower() not in ans_lower:
            failures.append(f"Agent did not ask for required info: '{item}'")

    # 5. required_sources
    for req_src in expect.get("required_sources", []):
        if req_src not in sources:
            failures.append(f"Missing required source: '{req_src}' (found sources: {sources})")

    # 6. forbidden_sources_as_authority
    for forb_src in expect.get("forbidden_sources_as_authority", []):
        if forb_src in sources:
            failures.append(f"Cited forbidden source as authority: '{forb_src}'")

    # 7. tool assertion
    expected_tool = expect.get("tool")
    if expected_tool == "not_called":
        if last_response.tool_called is not None:
            failures.append(f"Expected tool 'not_called', but tool '{last_response.tool_called}' was called")
    elif expected_tool == "order_lookup":
        if last_response.tool_called != "order_lookup":
            failures.append(f"Expected tool 'order_lookup', but got '{last_response.tool_called}'")
    elif expected_tool == "not_called_without_id":
        if last_response.tool_called is not None:
            failures.append("Tool should not be called without an order ID")

    # 8. tool_arguments
    expected_args = expect.get("tool_arguments")
    if expected_args:
        if last_response.tool_arguments != expected_args:
            failures.append(f"Tool arguments mismatch: expected {expected_args}, got {last_response.tool_arguments}")

    # 9. handoff
    expected_handoff = expect.get("handoff")
    if expected_handoff is not None:
        if last_response.handoff != expected_handoff:
            failures.append(f"Handoff mismatch: expected {expected_handoff}, got {last_response.handoff}")

    # 10. must_not_follow
    for nf in expect.get("must_not_follow", []):
        if "60" in nf and "60" in ans_lower:
            failures.append(f"Agent followed injected rule: '{nf}'")

    return (len(failures) == 0), failures


def run_all_evaluations():
    print("=" * 80)
    print(" Aster & Row Support Agent - Automated Evaluation Suite")
    print("=" * 80)

    visible_path = root_dir / "evaluation" / "visible-cases.json"
    custom_path = root_dir / "evaluation" / "custom-cases.json"

    with open(visible_path, "r", encoding="utf-8") as f:
        visible_data = json.load(f)
    visible_cases = visible_data.get("cases", [])

    custom_cases = []
    if custom_path.exists():
        with open(custom_path, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
        custom_cases = custom_data.get("cases", [])

    all_cases = [("Visible", c) for c in visible_cases] + [("Custom", c) for c in custom_cases]

    category_stats: Dict[str, Dict[str, int]] = {}
    passed_total = 0
    failed_total = 0

    agent = SupportAgent(debug=False)

    print(f"\nRunning {len(all_cases)} Evaluation Cases ({len(visible_cases)} visible, {len(custom_cases)} custom):\n")

    for suite_type, case in all_cases:
        case_id = case.get("id")
        category = case.get("category", "general")
        
        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0, "failed": 0}
        category_stats[category]["total"] += 1

        passed, failures = evaluate_case(case, agent)
        if passed:
            category_stats[category]["passed"] += 1
            passed_total += 1
            print(f"  [PASS] [{suite_type}] {case_id} ({category})")
        else:
            category_stats[category]["failed"] += 1
            failed_total += 1
            print(f"  [FAIL] [{suite_type}] {case_id} ({category})")
            for f in failures:
                print(f"         - {f}")

    print("\n" + "=" * 80)
    print(" Category Breakdown")
    print("=" * 80)
    print(f"{'Category':<28} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Pass Rate':<10}")
    print("-" * 64)
    for cat, stats in sorted(category_stats.items()):
        total = stats["total"]
        pass_cnt = stats["passed"]
        fail_cnt = stats["failed"]
        rate = f"{(pass_cnt / total * 100):.1f}%" if total > 0 else "N/A"
        print(f"{cat:<28} | {total:<6} | {pass_cnt:<6} | {fail_cnt:<6} | {rate:<10}")

    print("=" * 80)
    overall_rate = (passed_total / len(all_cases) * 100) if all_cases else 0.0
    print(f"TOTAL: {len(all_cases)} | PASSED: {passed_total} | FAILED: {failed_total} | PASS RATE: {overall_rate:.1f}%")
    print("=" * 80)

    if failed_total > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_evaluations()
