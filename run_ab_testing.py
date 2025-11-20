"""
A/B Testing Runner
Author: Leo Ji

Run A/B tests to compare different agent configurations.
"""

from evaluation.ab_testing_evaluator import ABTestingEvaluator, ABTestConfiguration

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           🧪 A/B Testing System                                    ║
║                                                                    ║
║  Compare different configurations and measure robustness           ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize evaluator
    print("🔧 Initializing A/B Testing Evaluator...")
    evaluator = ABTestingEvaluator(
        judge_model="gpt-4o-mini",
        judge_provider="openai"
    )
    print("✅ Ready!\n")
    
    # ========================================================================
    # STEP 1: Define Configurations
    # ========================================================================
    print("=" * 70)
    print("STEP 1: DEFINE TEST CONFIGURATIONS")
    print("=" * 70)
    print()
    print("📋 Available test scenarios:")
    print("  1. Basic vs Enhanced (agent_rules.md vs agent+analysis)")
    print("  2. Temperature Comparison (0.3 vs 0.7 vs 1.0)")
    print("  3. Custom (define your own)")
    print()
    
    scenario = input("Select scenario (1-3) [default: 1]: ").strip() or "1"
    
    if scenario == "1":
        # Basic vs Enhanced
        print("\n📊 Scenario: Basic vs Enhanced Analysis")
        print("   Control: Only core agent rules")
        print("   Treatment: Core rules + professional analysis rules")
        print()
        
        control = ABTestConfiguration(
            name="Control_BasicRules",
            rules_files=["agent_rules.md"],
            description="Baseline: Core agent rules only",
            temperature=0.7
        )
        
        treatment = ABTestConfiguration(
            name="Treatment_WithAnalysis",
            rules_files=["agent_rules.md", "analysis_rules.md"],
            description="Enhanced: Core + professional analysis rules",
            temperature=0.7
        )
        
        evaluator.add_configuration(control)
        evaluator.add_configuration(treatment)
    
    elif scenario == "2":
        # Temperature comparison
        print("\n📊 Scenario: Temperature Comparison")
        print("   Config A: temperature=0.3 (more deterministic)")
        print("   Config B: temperature=0.7 (balanced)")
        print("   Config C: temperature=1.0 (more creative)")
        print()
        
        config_a = ABTestConfiguration(
            name="Temperature_0.3",
            rules_files=["agent_rules.md", "analysis_rules.md"],
            description="Low temperature: deterministic responses",
            temperature=0.3
        )
        
        config_b = ABTestConfiguration(
            name="Temperature_0.7",
            rules_files=["agent_rules.md", "analysis_rules.md"],
            description="Medium temperature: balanced",
            temperature=0.7
        )
        
        config_c = ABTestConfiguration(
            name="Temperature_1.0",
            rules_files=["agent_rules.md", "analysis_rules.md"],
            description="High temperature: creative responses",
            temperature=1.0
        )
        
        evaluator.add_configuration(config_a)
        evaluator.add_configuration(config_b)
        evaluator.add_configuration(config_c)
    
    else:
        # Custom
        print("\n📊 Scenario: Custom Configuration")
        print("Using default: agent_rules.md + analysis_rules.md")
        
        custom = ABTestConfiguration(
            name="Custom_Config",
            rules_files=["agent_rules.md", "analysis_rules.md"],
            description="Custom configuration",
            temperature=0.7
        )
        
        evaluator.add_configuration(custom)
    
    # ========================================================================
    # STEP 2: Define Test Questions
    # ========================================================================
    print()
    print("=" * 70)
    print("STEP 2: DEFINE TEST QUESTIONS")
    print("=" * 70)
    print()
    print("📝 Question types:")
    print("  1. Options Search (basic queries)")
    print("  2. Options Analysis (sentiment, reports)")
    print("  3. Mixed (search + analysis)")
    print("  4. Custom (enter your own)")
    print()
    
    question_type = input("Select question type (1-4) [default: 3]: ").strip() or "3"
    
    if question_type == "1":
        test_questions = [
            "Get AAPL options for December 2025",
            "Search for TSLA options expiring in January 2026",
            "Find NVDA options for November 2025"
        ]
        print("\n✅ Using 3 options search questions")
    
    elif question_type == "2":
        test_questions = [
            "Analyze the sentiment of AAPL options for December 2025",
            "Generate a professional analysis report for TSLA November options",
            "Compare options sentiment between NVDA and AMD"
        ]
        print("\n✅ Using 3 analysis questions")
    
    elif question_type == "3":
        test_questions = [
            "Get AAPL options for December 2025",
            "Analyze TSLA options sentiment for November",
            "Compare NVDA and AMD options positioning"
        ]
        print("\n✅ Using 3 mixed questions")
    
    else:
        # Custom
        print("\n✏️  Enter your custom questions (one per line, empty line to finish):")
        test_questions = []
        while True:
            q = input(f"Question {len(test_questions)+1}: ").strip()
            if not q:
                break
            test_questions.append(q)
        
        if not test_questions:
            print("⚠️  No questions entered, using default")
            test_questions = [
                "Get AAPL options for December 2025",
                "Analyze TSLA sentiment",
                "Compare NVDA and AMD"
            ]
    
    print(f"\n📋 Test Questions:")
    for i, q in enumerate(test_questions, 1):
        print(f"   {i}. {q}")
    
    # ========================================================================
    # STEP 3: Configure Robustness Testing
    # ========================================================================
    print()
    print("=" * 70)
    print("STEP 3: CONFIGURE ROBUSTNESS TESTING")
    print("=" * 70)
    print()
    print("🔄 How many times should we run each question per configuration?")
    print("   (More runs = better robustness measurement, but slower)")
    print()
    print("   3 runs - Quick test (recommended for exploration)")
    print("   5 runs - Standard test (recommended for validation)")
    print("   10 runs - Thorough test (recommended for production)")
    print()
    
    runs = input("Number of runs per question (1-10) [default: 3]: ").strip()
    try:
        runs_per_question = int(runs) if runs else 3
        runs_per_question = max(1, min(10, runs_per_question))
    except:
        runs_per_question = 3
    
    print(f"\n✅ Will run each question {runs_per_question} times per configuration")
    
    # Calculate total runs
    total_configs = len(evaluator.configurations)
    total_questions = len(test_questions)
    total_runs = total_configs * total_questions * runs_per_question
    estimated_time = total_runs * 10  # Rough estimate: 10s per run
    
    print(f"\n📊 Test Summary:")
    print(f"   Configurations: {total_configs}")
    print(f"   Questions: {total_questions}")
    print(f"   Runs per question: {runs_per_question}")
    print(f"   Total runs: {total_runs}")
    print(f"   Estimated time: ~{estimated_time//60} minutes")
    
    # ========================================================================
    # STEP 4: Confirm and Run
    # ========================================================================
    print()
    confirm = input("▶️  Start A/B testing? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Test cancelled")
        return
    
    # ========================================================================
    # STEP 5: Run Tests
    # ========================================================================
    print()
    print("=" * 70)
    print("🧪 RUNNING A/B TESTS")
    print("=" * 70)
    print()
    
    try:
        comparison_results = evaluator.run_ab_comparison(
            questions=test_questions,
            config_names=None,  # Test all configurations
            runs_per_question=runs_per_question
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user (Ctrl+C)")
        print("💾 Saving partial results...")
        evaluator.save_results("data/ab_testing_partial.json")
        return
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================================================
    # STEP 6: Display Results
    # ========================================================================
    print()
    print("=" * 70)
    print("📊 TEST RESULTS")
    print("=" * 70)
    print()
    
    # Print comparison report
    evaluator.print_comparison_report(comparison_results)
    
    # ========================================================================
    # STEP 7: Detailed Robustness Reports (Optional)
    # ========================================================================
    print()
    print("=" * 70)
    print("📋 DETAILED ROBUSTNESS REPORTS")
    print("=" * 70)
    print()
    print("Would you like to see detailed robustness reports for specific tests?")
    show_detailed = input("(y/n) [default: n]: ").strip().lower()
    
    if show_detailed == 'y':
        print("\n📋 Available configurations:")
        config_names = list(evaluator.configurations.keys())
        for i, name in enumerate(config_names, 1):
            print(f"   {i}. {name}")
        
        print("\n📋 Available questions:")
        for i, q in enumerate(test_questions, 1):
            print(f"   {i}. {q[:50]}...")
        
        print()
        config_idx = input(f"Select configuration (1-{len(config_names)}): ").strip()
        question_idx = input(f"Select question (1-{len(test_questions)}): ").strip()
        
        try:
            config_name = config_names[int(config_idx) - 1]
            question = test_questions[int(question_idx) - 1]
            
            evaluator.print_robustness_report(config_name, question)
        except:
            print("⚠️  Invalid selection")
    
    # ========================================================================
    # STEP 8: Save Results
    # ========================================================================
    print()
    print("=" * 70)
    print("💾 SAVE RESULTS")
    print("=" * 70)
    print()
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"data/ab_testing_{timestamp}.json"
    
    filename = input(f"Save results to [{default_filename}]: ").strip()
    if not filename:
        filename = default_filename
    
    evaluator.save_results(filename)
    
    print()
    print("=" * 70)
    print("✅ A/B TESTING COMPLETE!")
    print("=" * 70)
    print()
    print("📊 Results Summary:")
    print(f"   Total tests run: {total_runs}")
    print(f"   Results saved: {filename}")
    print()
    print("💡 Next Steps:")
    print("   • Review the comparison report above")
    print("   • Check detailed results in JSON file")
    print("   • Use insights to optimize your agent configuration")
    print()
    
    # ========================================================================
    # STEP 9: Recommendations
    # ========================================================================
    print("=" * 70)
    print("🎯 KEY INSIGHTS")
    print("=" * 70)
    print()
    
    summary = comparison_results["summary"]
    
    # Find best performer
    best_config = max(summary.items(), key=lambda x: x[1]["mean_score"])
    most_robust = max(summary.items(), key=lambda x: x[1]["mean_robustness"])
    
    print(f"🏆 Best Overall Performance:")
    print(f"   {best_config[0]}")
    print(f"   Mean Score: {best_config[1]['mean_score']}/10")
    print()
    
    print(f"💪 Most Robust (Consistent):")
    print(f"   {most_robust[0]}")
    print(f"   Robustness Score: {most_robust[1]['mean_robustness']}/10")
    print()
    
    if best_config[0] == most_robust[0]:
        print("✅ Great news! The best performer is also the most robust.")
        print(f"   → Recommendation: Use '{best_config[0]}' configuration")
    else:
        print("⚠️  Best performer and most robust are different.")
        print(f"   → For production: Consider '{most_robust[0]}' (more reliable)")
        print(f"   → For exploration: Consider '{best_config[0]}' (higher scores)")
    
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

