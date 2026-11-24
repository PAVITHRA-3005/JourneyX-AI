"""Quick demo runner for JourneyX - writes output to demo_output_final.txt"""
import sys
import os

# LIVE MODE - use real LLM API from config/credentials.local.yaml
os.environ["JOURNEYX_AGENT_DRY_RUN"] = "false"
os.environ["JOURNEYX_EMBEDDING_FALLBACK"] = "false"
os.environ["JOURNEYX_DISABLE_RERANK"] = "true"   # skip heavy cross-encoder

sys.path.insert(0, "packages")

output_lines = []

def run_query(label, query):
    output_lines.append(f"\n{'='*60}")
    output_lines.append(f"QUERY: {query}")
    output_lines.append('='*60)
    try:
        from journeyx.orchestration import run_turn
        result = run_turn(query)
        output_lines.append(f"STATUS: {result.get('status', 'unknown')}")
        output_lines.append(f"INTENT: {result.get('planner_intent', 'unknown')}")
        output_lines.append(f"STEPS: {result.get('step_count', 0)}")
        output_lines.append(f"TOOL CALLS: {result.get('tool_calls', 0)}")
        output_lines.append(f"\nRESPONSE:\n{result.get('response', 'No response')}")
    except Exception as e:
        output_lines.append(f"ERROR: {e}")
        import traceback
        output_lines.append(traceback.format_exc())

# Test 1: Refusal
run_query("REFUSAL", "Book me a train ticket to Jaipur")

# Test 2: Transport Compare
run_query("TRANSPORT", "Compare train and bus from Delhi to Jaipur")

# Test 3: Full Plan
run_query("FULL PLAN", "Plan 3 days in Jaipur from Delhi for 2 people under 20000 by train")

# Write output
with open("demo_output_final.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Demo complete - see demo_output_final.txt")
