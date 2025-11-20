"""
A/B Testing Evaluator - Advanced Testing System
Author: Leo Ji

A sophisticated evaluation system that:
1. Tests different configurations (control variables)
2. Measures robustness (consistency across multiple runs)
3. Compares performance metrics
4. Generates statistical analysis
"""

import json
import time
import statistics
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.llm_judge import LLMJudge
from utils.rules_loader import RulesLoader


class ABTestConfiguration:
    """
    Configuration for an A/B test variant.
    
    Each configuration represents one "treatment" in the experiment.
    """
    
    def __init__(
        self,
        name: str,
        rules_files: List[str],
        description: str = "",
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize test configuration.
        
        Args:
            name: Configuration name (e.g., "Control", "Treatment_A")
            rules_files: List of rules markdown files to load
            description: What this configuration tests
            model_name: LLM model to use
            temperature: Model temperature
            metadata: Additional configuration metadata
        """
        self.name = name
        self.rules_files = rules_files
        self.description = description
        self.model_name = model_name
        self.temperature = temperature
        self.metadata = metadata or {}
        
        # Load rules
        self.rules_content = self._load_rules()
    
    def _load_rules(self) -> str:
        """Load and combine all rules files."""
        loader = RulesLoader()
        combined_rules = []
        
        for rules_file in self.rules_files:
            try:
                content = loader.load_rules(rules_file)
                combined_rules.append(f"# From: {rules_file}\n\n{content}")
            except Exception as e:
                print(f"⚠️  Warning: Could not load {rules_file}: {e}")
        
        return "\n\n---\n\n".join(combined_rules)
    
    def get_system_prompt(self) -> str:
        """Get the complete system prompt for this configuration."""
        return self.rules_content


class ABTestingEvaluator:
    """
    Advanced A/B Testing system for agent evaluation.
    
    Features:
    - Control variable testing
    - Robustness measurement
    - Statistical analysis
    - Comparative reporting
    """
    
    def __init__(
        self,
        judge_model: str = "gpt-4o-mini",
        judge_provider: str = "openai"
    ):
        """
        Initialize A/B testing evaluator.
        
        Args:
            judge_model: Model for judging responses
            judge_provider: Provider for judge model
        """
        self.judge = LLMJudge(judge_model, judge_provider)
        self.test_results: Dict[str, List[Dict[str, Any]]] = {}
        self.configurations: Dict[str, ABTestConfiguration] = {}
    
    def add_configuration(self, config: ABTestConfiguration):
        """
        Add a configuration to test.
        
        Args:
            config: Test configuration
        """
        self.configurations[config.name] = config
        self.test_results[config.name] = []
        print(f"✅ Added configuration: {config.name}")
        if config.description:
            print(f"   Description: {config.description}")
    
    def run_robustness_test(
        self,
        question: str,
        config_name: str,
        num_runs: int = 5,
        thread_id_base: str = "robustness_test"
    ) -> Dict[str, Any]:
        """
        Test robustness by running the same question multiple times.
        
        Args:
            question: Question to test
            config_name: Which configuration to test
            num_runs: Number of times to run the same question
            thread_id_base: Base thread ID
            
        Returns:
            Robustness analysis results
        """
        if config_name not in self.configurations:
            raise ValueError(f"Configuration '{config_name}' not found")
        
        config = self.configurations[config_name]
        
        print(f"\n{'='*70}")
        print(f"🔬 ROBUSTNESS TEST: {config_name}")
        print(f"{'='*70}")
        print(f"Question: {question}")
        print(f"Runs: {num_runs}")
        print()
        
        responses = []
        scores = []
        execution_times = []
        
        for run in range(num_runs):
            print(f"Run {run + 1}/{num_runs}...", end=" ")
            
            # Create agent with this configuration
            agent = self._create_agent_with_config(config)
            
            # Execute query
            start_time = time.time()
            response_text = self._call_agent(
                agent,
                question,
                thread_id=f"{thread_id_base}_{run}"
            )
            execution_time = time.time() - start_time
            
            # Evaluate response
            evaluation = self.judge.evaluate_response(
                query=question,
                response=response_text,
                context=""
            )
            
            score = evaluation.get("overall_score", 0) if evaluation.get("status") == "success" else 0
            
            responses.append(response_text)
            scores.append(score)
            execution_times.append(execution_time)
            
            print(f"Score: {score}/10, Time: {execution_time:.2f}s")
        
        # Calculate robustness metrics
        robustness_analysis = self._calculate_robustness_metrics(
            responses, scores, execution_times
        )
        
        # Store results
        result = {
            "config_name": config_name,
            "question": question,
            "num_runs": num_runs,
            "responses": responses,
            "scores": scores,
            "execution_times": execution_times,
            "robustness_analysis": robustness_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results[config_name].append(result)
        
        return robustness_analysis
    
    def run_ab_comparison(
        self,
        questions: List[str],
        config_names: Optional[List[str]] = None,
        runs_per_question: int = 3
    ) -> Dict[str, Any]:
        """
        Run A/B comparison across multiple configurations.
        
        Args:
            questions: List of test questions
            config_names: Which configurations to test (None = all)
            runs_per_question: Number of runs per question per config
            
        Returns:
            Comparative analysis results
        """
        if config_names is None:
            config_names = list(self.configurations.keys())
        
        print(f"\n{'='*70}")
        print(f"🧪 A/B COMPARISON TEST")
        print(f"{'='*70}")
        print(f"Configurations: {', '.join(config_names)}")
        print(f"Questions: {len(questions)}")
        print(f"Runs per question: {runs_per_question}")
        print(f"Total runs: {len(config_names) * len(questions) * runs_per_question}")
        print()
        
        comparison_results = {}
        
        for config_name in config_names:
            print(f"\n📊 Testing: {config_name}")
            print("-" * 70)
            
            config_results = []
            
            for i, question in enumerate(questions, 1):
                print(f"\nQuestion {i}/{len(questions)}: {question[:50]}...")
                
                # Run robustness test for this question
                robustness = self.run_robustness_test(
                    question=question,
                    config_name=config_name,
                    num_runs=runs_per_question,
                    thread_id_base=f"ab_test_{config_name}_q{i}"
                )
                
                config_results.append({
                    "question": question,
                    "robustness": robustness
                })
            
            comparison_results[config_name] = config_results
        
        # Generate comparative analysis
        comparative_analysis = self._generate_comparative_analysis(
            comparison_results,
            questions
        )
        
        return comparative_analysis
    
    def _calculate_robustness_metrics(
        self,
        responses: List[str],
        scores: List[float],
        execution_times: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate robustness metrics from multiple runs.
        
        Args:
            responses: List of response texts
            scores: List of scores
            execution_times: List of execution times
            
        Returns:
            Robustness metrics
        """
        # Score statistics
        mean_score = statistics.mean(scores)
        stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0
        min_score = min(scores)
        max_score = max(scores)
        
        # Time statistics
        mean_time = statistics.mean(execution_times)
        stdev_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        # Response similarity (simple: length-based)
        response_lengths = [len(r) for r in responses]
        length_stdev = statistics.stdev(response_lengths) if len(response_lengths) > 1 else 0
        
        # Consistency score (lower stdev = more consistent)
        consistency_score = max(0, 10 - (stdev_score * 5))  # Scale to 0-10
        
        # Overall robustness score
        robustness_score = (
            (mean_score * 0.5) +  # Quality (50%)
            (consistency_score * 0.3) +  # Consistency (30%)
            (max(0, 10 - stdev_time) * 0.2)  # Time stability (20%)
        )
        
        return {
            "score_stats": {
                "mean": round(mean_score, 2),
                "stdev": round(stdev_score, 2),
                "min": round(min_score, 2),
                "max": round(max_score, 2)
            },
            "time_stats": {
                "mean": round(mean_time, 2),
                "stdev": round(stdev_time, 2)
            },
            "response_consistency": {
                "length_stdev": round(length_stdev, 2),
                "consistency_score": round(consistency_score, 2)
            },
            "robustness_score": round(robustness_score, 2),
            "interpretation": self._interpret_robustness(stdev_score, consistency_score)
        }
    
    def _interpret_robustness(
        self,
        score_stdev: float,
        consistency_score: float
    ) -> str:
        """Interpret robustness metrics."""
        if score_stdev < 0.5 and consistency_score > 8:
            return "🟢 Excellent - Highly consistent responses"
        elif score_stdev < 1.0 and consistency_score > 6:
            return "🟡 Good - Reasonably consistent"
        elif score_stdev < 2.0:
            return "🟠 Moderate - Some variability in responses"
        else:
            return "🔴 Poor - High variability, inconsistent responses"
    
    def _generate_comparative_analysis(
        self,
        comparison_results: Dict[str, List[Dict[str, Any]]],
        questions: List[str]
    ) -> Dict[str, Any]:
        """Generate comparative analysis across configurations."""
        analysis = {
            "summary": {},
            "by_question": {},
            "statistical_significance": {},
            "recommendations": []
        }
        
        # Aggregate metrics by configuration
        for config_name, results in comparison_results.items():
            all_scores = []
            all_robustness = []
            
            for result in results:
                robustness = result["robustness"]
                all_scores.append(robustness["score_stats"]["mean"])
                all_robustness.append(robustness["robustness_score"])
            
            analysis["summary"][config_name] = {
                "mean_score": round(statistics.mean(all_scores), 2),
                "mean_robustness": round(statistics.mean(all_robustness), 2),
                "questions_tested": len(results)
            }
        
        # By question comparison
        for i, question in enumerate(questions):
            question_key = f"q{i+1}"
            analysis["by_question"][question_key] = {
                "question": question,
                "configs": {}
            }
            
            for config_name, results in comparison_results.items():
                if i < len(results):
                    robustness = results[i]["robustness"]
                    analysis["by_question"][question_key]["configs"][config_name] = {
                        "mean_score": robustness["score_stats"]["mean"],
                        "robustness": robustness["robustness_score"]
                    }
        
        # Generate recommendations
        best_overall = max(
            analysis["summary"].items(),
            key=lambda x: x[1]["mean_score"]
        )
        most_robust = max(
            analysis["summary"].items(),
            key=lambda x: x[1]["mean_robustness"]
        )
        
        analysis["recommendations"] = [
            f"Best overall performance: {best_overall[0]} (score: {best_overall[1]['mean_score']})",
            f"Most robust: {most_robust[0]} (robustness: {most_robust[1]['mean_robustness']})"
        ]
        
        return analysis
    
    def _create_agent_with_config(self, config: ABTestConfiguration):
        """Create an agent instance with specific configuration."""
        # Import here to avoid circular dependencies
        from langchain.chat_models import init_chat_model
        from langchain_core.messages import SystemMessage
        
        # Initialize LLM with config parameters
        llm = init_chat_model(
            config.model_name,
            model_provider="openai",
            temperature=config.temperature
        )
        
        # Return a simple wrapper that uses the config's system prompt
        class ConfiguredAgent:
            def __init__(self, llm, system_prompt):
                self.llm = llm
                self.system_prompt = system_prompt
            
            def invoke(self, query):
                messages = [
                    SystemMessage(content=self.system_prompt),
                    {"role": "user", "content": query}
                ]
                response = self.llm.invoke(messages)
                return response.content
        
        return ConfiguredAgent(llm, config.get_system_prompt())
    
    def _call_agent(
        self,
        agent,
        query: str,
        thread_id: str = "test"
    ) -> str:
        """Call agent and get response."""
        try:
            return agent.invoke(query)
        except Exception as e:
            print(f"\n⚠️  Error calling agent: {e}")
            return f"Error: {str(e)}"
    
    def print_robustness_report(self, config_name: str, question: str):
        """Print detailed robustness report for a specific test."""
        # Find the test result
        results = self.test_results.get(config_name, [])
        test_result = None
        
        for result in results:
            if result["question"] == question:
                test_result = result
                break
        
        if not test_result:
            print(f"❌ No results found for {config_name} / {question}")
            return
        
        robustness = test_result["robustness_analysis"]
        
        print(f"\n{'='*70}")
        print(f"📊 ROBUSTNESS REPORT")
        print(f"{'='*70}")
        print(f"Configuration: {config_name}")
        print(f"Question: {question}")
        print(f"Runs: {test_result['num_runs']}")
        print()
        
        print(f"🎯 Score Statistics:")
        score_stats = robustness["score_stats"]
        print(f"   Mean: {score_stats['mean']}/10")
        print(f"   StdDev: {score_stats['stdev']}")
        print(f"   Range: {score_stats['min']} - {score_stats['max']}")
        print()
        
        print(f"⏱️  Time Statistics:")
        time_stats = robustness["time_stats"]
        print(f"   Mean: {time_stats['mean']:.2f}s")
        print(f"   StdDev: {time_stats['stdev']:.2f}s")
        print()
        
        print(f"🔄 Consistency:")
        consistency = robustness["response_consistency"]
        print(f"   Consistency Score: {consistency['consistency_score']}/10")
        print(f"   Response Length StdDev: {consistency['length_stdev']}")
        print()
        
        print(f"💪 Overall Robustness: {robustness['robustness_score']}/10")
        print(f"   {robustness['interpretation']}")
        print()
    
    def print_comparison_report(self, comparison_results: Dict[str, Any]):
        """Print comparative analysis report."""
        print(f"\n{'='*70}")
        print(f"📊 A/B COMPARISON REPORT")
        print(f"{'='*70}")
        print()
        
        print(f"📈 Summary by Configuration:")
        print()
        
        summary = comparison_results["summary"]
        for config_name, metrics in summary.items():
            print(f"   {config_name}:")
            print(f"      Mean Score: {metrics['mean_score']}/10")
            print(f"      Mean Robustness: {metrics['mean_robustness']}/10")
            print(f"      Questions Tested: {metrics['questions_tested']}")
            print()
        
        print(f"🏆 Recommendations:")
        for rec in comparison_results["recommendations"]:
            print(f"   • {rec}")
        print()
        
        print(f"📋 Detailed Results by Question:")
        print()
        
        for q_key, q_data in comparison_results["by_question"].items():
            print(f"   {q_key}: {q_data['question'][:50]}...")
            for config_name, metrics in q_data["configs"].items():
                print(f"      {config_name}: Score={metrics['mean_score']}, " +
                      f"Robustness={metrics['robustness']}")
            print()
    
    def save_results(self, filepath: str = "data/ab_testing_results.json"):
        """Save all test results to file."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        output = {
            "configurations": {
                name: {
                    "rules_files": config.rules_files,
                    "description": config.description,
                    "model_name": config.model_name,
                    "temperature": config.temperature
                }
                for name, config in self.configurations.items()
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✅ Results saved to {filepath}")


# Example usage
if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           🧪 A/B Testing Evaluator                                 ║
║                                                                    ║
║  Advanced testing system for comparing configurations              ║
║  and measuring robustness                                          ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize evaluator
    evaluator = ABTestingEvaluator()
    
    # Define configurations to test
    control_config = ABTestConfiguration(
        name="Control",
        rules_files=["agent_rules.md"],
        description="Baseline: Only core agent rules"
    )
    
    treatment_config = ABTestConfiguration(
        name="Treatment_WithAnalysis",
        rules_files=["agent_rules.md", "analysis_rules.md"],
        description="Enhanced: Core rules + specialized analysis rules"
    )
    
    # Add configurations
    evaluator.add_configuration(control_config)
    evaluator.add_configuration(treatment_config)
    
    # Test questions
    test_questions = [
        "Get AAPL options for December 2025",
        "Analyze TSLA options sentiment for November",
        "Compare NVDA and AMD options positioning"
    ]
    
    # Run A/B comparison
    comparison = evaluator.run_ab_comparison(
        questions=test_questions,
        runs_per_question=3
    )
    
    # Print report
    evaluator.print_comparison_report(comparison)
    
    # Save results
    evaluator.save_results()

