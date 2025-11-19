"""
Agent Evaluation Runner
Author: Leo Ji

Run automated evaluation with LLM-generated questions and scoring.
"""

from evaluation.external_evaluator import ExternalEvaluator

print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           🤖 Agent Evaluation System                               ║
║                                                                    ║
║  LLM generates questions → Agent answers → LLM scores              ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
""")

# Initialize
print("🔧 Initializing evaluator...")
evaluator = ExternalEvaluator(model_name="gpt-4o-mini", model_provider="openai")
print("✅ Ready!\n")

# Step 1: Generate questions using LLM (动态生成，不是硬编码)
print("=" * 70)
print("STEP 1: LLM GENERATES TEST QUESTIONS")
print("=" * 70)
print()

count = int(input("How many test questions? (1-10) [default: 3]: ").strip() or "3")
count = max(1, min(10, count))

print(f"\n🤖 Using LLM to generate {count} test questions...")
print("   (Focus: Options trading, mixed difficulty)")
print()

questions = evaluator.generate_dynamic_test_questions(
    focus_area="options trading and analysis",
    difficulty="mixed",
    count=count
)

print(f"✅ Generated {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"   {i}. {q}")
print()

# Step 2: Run agent tests
confirm = input("▶️  Continue to run tests? (y/n): ").strip().lower()
if confirm != 'y':
    print("❌ Cancelled")
    exit()

print()
print("=" * 70)
print("STEP 2: AGENT ANSWERS QUESTIONS")
print("=" * 70)
print()

try:
    summary = evaluator.run_test_suite(
        questions=questions,
        suite_name="LLM-Generated Test Suite"
    )
except KeyboardInterrupt:
    print("\n\n⚠️  Test interrupted by user (Ctrl+C)")
    print("💡 Tip: Some questions may be complex and take 1-2 minutes")
    exit()
except Exception as e:
    print(f"\n\n❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    exit()

# Step 3: Show results
print()
print("=" * 70)
print("STEP 3: LLM JUDGE SCORES THE ANSWERS")
print("=" * 70)
print()

evaluator.print_summary_report()

# Save results
import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filepath = f"data/evaluation_{timestamp}.json"
evaluator.save_results(filepath)

print(f"\n💾 Results saved to: {filepath}")
print("\n✅ Evaluation complete!\n")

