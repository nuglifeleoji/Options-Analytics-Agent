"""
External Evaluator - Automated Testing and Benchmarking System

This is an independent evaluation tool that:
1. Generates test questions automatically
2. Calls the main agent (search_tools.py)
3. Evaluates response quality using LLM Judge
4. Generates comprehensive test reports

Author: Leo Ji
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.llm_judge import LLMJudge, print_evaluation_report

# Try to import from agent_main first, fallback to backup
try:
    from agent_main import graph, config
    default_config = config
except ImportError:
    try:
        from backup import graph, config as default_config
    except ImportError:
        print("⚠️  Warning: Could not import agent. Make sure agent_main.py or backup.py exists.")
        graph = None
        default_config = {"configurable": {"thread_id": "evaluator"}}


class ExternalEvaluator:
    """
    External evaluation system for testing and benchmarking the agent.
    
    This system operates independently from the main agent and can:
    - Generate test questions automatically
    - Execute tests against the agent
    - Evaluate responses comprehensively
    - Generate detailed test reports
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", model_provider: str = "openai"):
        """
        Initialize the external evaluator.
        
        Args:
            model_name: LLM model for judging
            model_provider: Provider (openai, anthropic, etc.)
        """
        self.judge = LLMJudge(model_name, model_provider)
        self.test_results: List[Dict[str, Any]] = []
        self.test_suite_name = ""
        
        # Initialize LLM for dynamic question generation
        from langchain.chat_models import init_chat_model
        self.question_generator = init_chat_model(model_name, model_provider=model_provider)
        
    def generate_test_questions(self, category: str = "general", count: int = 5) -> List[str]:
        """
        Generate test questions automatically for evaluating the agent.
        
        Args:
            category: Category of questions (e.g., "general", "options", "data_export")
            count: Number of questions to generate
        
        Returns:
            List of test questions
        """
        # Predefined test questions by category
        test_questions = {
            "general": [
                "What can you do?",
                "How do I get options data for Apple?",
                "Can you show me a chart?",
                "What tools do you have available?",
                "Help me find options for Tesla"
            ],
            "options": [
                "Get AAPL options for December 2025",
                "Show me TSLA options expiring in January",
                "Find options for Microsoft for next month",
                "Get all options for GOOGL in November",
                "Search for NVDA options"
            ],
            "data_export": [
                "Export AAPL options to CSV",
                "Create a table for Tesla options",
                "Save the data to a file",
                "Generate a CSV export",
                "Make an options table"
            ],
            "visualization": [
                "Show me a chart of AAPL options",
                "Create a plot for the options data",
                "Generate a visualization",
                "Make a butterfly chart",
                "Plot the options chain"
            ],
            "complex": [
                "Get AAPL options for December and export to CSV",
                "Show me Tesla options and create a chart",
                "Find Microsoft options and save the data",
                "Get options for GOOGL and visualize them",
                "Search NVDA options, export and plot"
            ]
        }
        
        questions = test_questions.get(category, test_questions["general"])
        return questions[:count]
    
    def generate_dynamic_test_questions(
        self, 
        focus_area: str = "options trading",
        difficulty: str = "mixed",
        count: int = 5,
        agent_capabilities: Optional[str] = None
    ) -> List[str]:
        """
        🆕 Dynamically generate test questions using LLM (not hardcoded).
        
        This method uses an LLM to intelligently generate test questions based on:
        - The agent's capabilities
        - Desired focus area
        - Difficulty level
        - Coverage requirements
        
        Args:
            focus_area: Area to focus on (e.g., "options trading", "data analysis", "visualization")
            difficulty: Question difficulty ("easy", "medium", "hard", "mixed")
            count: Number of questions to generate
            agent_capabilities: Description of what the agent can do (if None, uses default)
        
        Returns:
            List of dynamically generated test questions
        """
        # Default agent capabilities description
        if agent_capabilities is None:
            agent_capabilities = """
            This is a Financial Options Analysis Agent with the following capabilities:
            
            1. Options Data Search:
               - Search for stock options by ticker and date
               - Batch search for multiple tickers
               - Support for specific dates (YYYY-MM-DD) or entire months (YYYY-MM)
            
            2. Data Export:
               - Export options data to CSV files
               - Create custom CSV formats using dynamic code execution
            
            3. Visualization:
               - Generate butterfly charts (symmetric bar charts)
               - Create PNG visualizations of options chains
            
            4. Professional Analysis:
               - Analyze options chain sentiment (bullish/bearish/neutral)
               - Generate professional analysis reports
               - Compare sentiment between different tickers
               - Identify key strike levels and market structure
            
            5. Knowledge Base (RAG):
               - Store and retrieve historical options data
               - Smart caching to avoid repeated API calls
               - Anomaly detection using vector similarity
               - Batch collection and storage
            
            6. Web Search:
               - Look up ticker symbols from company names
               - Search for general information
            
            7. Code Execution:
               - Execute custom Python code for data processing
               - Generate custom CSV formats based on user requirements
            
            8. Performance Monitoring:
               - Track execution time, token usage, and costs
               - Provide performance statistics on demand
            """
        
        # Construct prompt for question generation
        prompt = f"""You are a test question generator for an AI agent evaluation system.

**Agent Capabilities:**
{agent_capabilities}

**Your Task:**
Generate {count} diverse, realistic test questions that evaluate this agent's capabilities.

**Requirements:**
- Focus Area: {focus_area}
- Difficulty: {difficulty}
- Questions should be natural, as a real user would ask
- Cover different aspects of the agent's capabilities
- Include both simple and complex scenarios
- Mix single-step and multi-step tasks
- Use real stock ticker symbols (AAPL, TSLA, MSFT, GOOGL, NVDA, etc.)

**Difficulty Guidelines:**
- Easy: Single, straightforward requests
- Medium: Requests with some specificity or 2 steps
- Hard: Complex multi-step tasks or edge cases
- Mixed: Combination of all levels

**Output Format:**
Return ONLY a JSON array of question strings, nothing else.
Example: ["question 1", "question 2", "question 3"]

Generate {count} questions now:"""

        try:
            # Call LLM to generate questions
            response = self.question_generator.invoke([{"role": "user", "content": prompt}])
            
            # Parse response
            content = response.content.strip()
            
            # Try to extract JSON array from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                questions_json = json_match.group(0)
                questions = json.loads(questions_json)
                
                # Validate and clean
                questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
                
                if len(questions) > 0:
                    print(f"✅ Generated {len(questions)} dynamic test questions")
                    return questions[:count]
            
            # Fallback if parsing fails
            print("⚠️  Failed to parse LLM response, using fallback questions")
            return self.generate_test_questions(category="options", count=count)
            
        except Exception as e:
            print(f"⚠️  Error generating dynamic questions: {e}")
            print("   Using fallback predefined questions")
            return self.generate_test_questions(category="options", count=count)
    
    def call_agent(self, query: str, thread_id: str = "evaluator") -> tuple[str, float]:
        """
        Call the agent with a query and get the response.
        
        Args:
            query: User query to test
            thread_id: Thread ID for this test session
        
        Returns:
            Tuple of (response_text, execution_time)
        """
        config = {"configurable": {"thread_id": thread_id}}
        response_text = ""
        start_time = time.time()
        
        try:
            for event in graph.stream({"messages": [{"role": "user", "content": query}]}, config):
                for value in event.values():
                    if isinstance(value, dict) and "messages" in value:
                        message = value["messages"][-1]
                        if hasattr(message, 'content'):
                            response_text = message.content
            
            execution_time = time.time() - start_time
            return response_text, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return f"ERROR: {str(e)}", execution_time
    
    def run_single_test(self, query: str, thread_id: str = "evaluator") -> Dict[str, Any]:
        """
        Run a single test: call agent + evaluate response.
        
        Args:
            query: Test question
            thread_id: Thread ID for isolation
        
        Returns:
            Test result dictionary
        """
        print(f"\n🧪 Testing: {query}")
        
        # Call agent
        response, execution_time = self.call_agent(query, thread_id)
        print(f"⏱️  Execution time: {execution_time:.2f}s")
        
        # Evaluate response
        evaluation = self.judge.evaluate_response(query, response)
        
        # Compile test result
        test_result = {
            "query": query,
            "response": response[:200] + "..." if len(response) > 200 else response,
            "full_response": response,
            "execution_time": execution_time,
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
        
        # Display evaluation
        if evaluation.get("status") == "success":
            overall_score = evaluation.get("overall_score", 0)
            emoji = "🟢" if overall_score >= 8 else "🟡" if overall_score >= 6 else "🔴"
            print(f"{emoji} Score: {overall_score:.1f}/10")
        
        return test_result
    
    def run_test_suite(
        self,
        questions: List[str],
        suite_name: str = "General Test Suite",
        thread_prefix: str = "eval"
    ) -> Dict[str, Any]:
        """
        Run a full test suite with multiple questions.
        
        Args:
            questions: List of test questions
            suite_name: Name of this test suite
            thread_prefix: Prefix for thread IDs (each test gets unique thread)
        
        Returns:
            Test suite summary
        """
        print(f"\n{'='*70}")
        print(f"🚀 Starting Test Suite: {suite_name}")
        print(f"{'='*70}")
        print(f"Total tests: {len(questions)}\n")
        
        self.test_suite_name = suite_name
        self.test_results = []
        
        for i, question in enumerate(questions, 1):
            print(f"\n[Test {i}/{len(questions)}]")
            
            # Each test gets isolated thread
            thread_id = f"{thread_prefix}_{i}_{int(time.time())}"
            
            test_result = self.run_single_test(question, thread_id)
            self.test_results.append(test_result)
            
            # Small delay between tests
            time.sleep(0.5)
        
        # Generate summary
        summary = self._generate_summary()
        
        print(f"\n{'='*70}")
        print(f"✅ Test Suite Complete")
        print(f"{'='*70}\n")
        
        return summary
    
    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics from test results.
        
        Returns:
            Summary dictionary
        """
        if not self.test_results:
            return {"message": "No test results available"}
        
        total_tests = len(self.test_results)
        successful_evals = [
            r for r in self.test_results 
            if r.get("evaluation", {}).get("status") == "success"
        ]
        
        # Calculate statistics
        scores = [
            r["evaluation"]["overall_score"] 
            for r in successful_evals
        ]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
        else:
            avg_score = min_score = max_score = 0
        
        avg_execution_time = sum(r["execution_time"] for r in self.test_results) / total_tests
        
        # Dimension averages
        dimension_scores = {
            "relevance": [],
            "accuracy": [],
            "completeness": [],
            "helpfulness": []
        }
        
        for result in successful_evals:
            dims = result.get("evaluation", {}).get("dimensions", {})
            for dim in dimension_scores.keys():
                if dim in dims:
                    dimension_scores[dim].append(dims[dim].get("score", 0))
        
        dimension_averages = {
            dim: sum(scores) / len(scores) if scores else 0
            for dim, scores in dimension_scores.items()
        }
        
        # Pass rate (score >= 6.0)
        passed = sum(1 for s in scores if s >= 6.0)
        pass_rate = (passed / len(scores) * 100) if scores else 0
        
        summary = {
            "suite_name": self.test_suite_name,
            "total_tests": total_tests,
            "successful_evaluations": len(successful_evals),
            "overall_statistics": {
                "average_score": round(avg_score, 2),
                "min_score": round(min_score, 2),
                "max_score": round(max_score, 2),
                "pass_rate": round(pass_rate, 1),
                "average_execution_time": round(avg_execution_time, 2)
            },
            "dimension_averages": {
                k: round(v, 2) for k, v in dimension_averages.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def print_summary_report(self):
        """
        Print a formatted summary report of the test results.
        """
        if not self.test_results:
            print("No test results to display.")
            return
        
        summary = self._generate_summary()
        
        print("\n" + "="*70)
        print(f"📊 TEST SUITE SUMMARY: {summary['suite_name']}")
        print("="*70)
        
        print(f"\n📈 Overall Statistics:")
        stats = summary['overall_statistics']
        print(f"   • Total Tests: {summary['total_tests']}")
        print(f"   • Average Score: {stats['average_score']}/10")
        print(f"   • Score Range: {stats['min_score']} - {stats['max_score']}")
        print(f"   • Pass Rate (≥6.0): {stats['pass_rate']}%")
        print(f"   • Avg Execution Time: {stats['average_execution_time']}s")
        
        print(f"\n📋 Dimension Averages:")
        dims = summary['dimension_averages']
        for dim, score in dims.items():
            emoji = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
            print(f"   {emoji} {dim.capitalize()}: {score}/10")
        
        print(f"\n📝 Individual Test Results:")
        for i, result in enumerate(self.test_results, 1):
            eval_data = result.get("evaluation", {})
            if eval_data.get("status") == "success":
                score = eval_data.get("overall_score", 0)
                emoji = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
            else:
                score = "N/A"
                emoji = "❌"
            
            print(f"\n   {i}. {result['query'][:50]}...")
            print(f"      {emoji} Score: {score}/10 | Time: {result['execution_time']:.2f}s")
        
        print("\n" + "="*70 + "\n")
    
    def save_results(self, filepath: str = "data/evaluation_results.json"):
        """
        Save test results to a JSON file.
        
        Args:
            filepath: Path to save results
        """
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        output = {
            "summary": self._generate_summary(),
            "detailed_results": self.test_results
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✅ Results saved to {filepath}")


# Example usage
if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           🧪 External Evaluator - Agent Testing System             ║
║                                                                    ║
║  This tool independently tests and evaluates the agent's           ║
║  performance across multiple dimensions.                           ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize evaluator
    evaluator = ExternalEvaluator()
    
    # Generate test questions
    print("📝 Generating test questions...")
    questions = evaluator.generate_test_questions(category="options", count=3)
    
    # Run test suite
    summary = evaluator.run_test_suite(
        questions=questions,
        suite_name="Options Search Test Suite"
    )
    
    # Print summary report
    evaluator.print_summary_report()
    
    # Save results
    evaluator.save_results()

