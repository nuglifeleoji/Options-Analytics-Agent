
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMJudge:
    """
    Independent LLM-based judge for evaluating agent responses.
    
    This judge operates independently from the main agent and provides
    objective assessments of response quality across multiple dimensions.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", model_provider: str = "openai"):
        """
        Initialize the LLM Judge.
        
        Args:
            model_name: Name of the LLM model to use for judging
            model_provider: Provider of the LLM (e.g., "openai", "anthropic")
        """
        self.llm = init_chat_model(model_name, model_provider=model_provider)
        self.evaluation_history: List[Dict[str, Any]] = []
        
    def evaluate_response(
        self,
        user_query: str,
        agent_response: str,
        context: Optional[str] = None,
        evaluation_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate an agent response against multiple quality dimensions.
        
        Args:
            user_query: The original user question/request
            agent_response: The agent's response to evaluate
            context: Optional additional context (e.g., retrieved data, tool outputs)
            evaluation_criteria: Optional list of specific criteria to evaluate
                                Default: ["relevance", "accuracy", "completeness", "helpfulness"]
        
        Returns:
            Dictionary containing scores and detailed feedback for each dimension
        """
        if evaluation_criteria is None:
            evaluation_criteria = ["relevance", "accuracy", "completeness", "helpfulness"]
        
        # Build evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            user_query, 
            agent_response, 
            context, 
            evaluation_criteria
        )
        
        # Get LLM judgment
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=evaluation_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            evaluation_result = self._parse_evaluation_response(response.content)
            
            # Add metadata
            evaluation_result["timestamp"] = datetime.now().isoformat()
            evaluation_result["user_query"] = user_query
            evaluation_result["agent_response"] = agent_response[:200] + "..." if len(agent_response) > 200 else agent_response
            
            # Store in history
            self.evaluation_history.append(evaluation_result)
            
            return evaluation_result
            
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the judge LLM.
        
        Returns:
            System prompt string
        """
        return """You are an expert evaluator assessing the quality of AI agent responses.

Your role is to provide objective, constructive evaluations across multiple dimensions:

1. **Relevance (0-10)**: Does the response directly address the user's query?
   - 10: Perfectly aligned with user intent
   - 5: Partially relevant but missing key aspects
   - 0: Completely off-topic

2. **Accuracy (0-10)**: Is the information factually correct and truthful?
   - 10: All information is accurate and verifiable
   - 5: Some inaccuracies or unverified claims
   - 0: Contains false or misleading information

3. **Completeness (0-10)**: Does the response fully answer the question?
   - 10: Comprehensive, addresses all aspects
   - 5: Addresses main points but misses some details
   - 0: Incomplete or superficial

4. **Helpfulness (0-10)**: Is the response useful and actionable?
   - 10: Extremely helpful, provides clear guidance
   - 5: Somewhat helpful but could be improved
   - 0: Not helpful or confusing

For each dimension, provide:
- A numerical score (0-10)
- A brief explanation (1-2 sentences)
- Specific suggestions for improvement (if score < 8)

Return your evaluation in the following JSON format:
{
    "overall_score": <average of all dimensions>,
    "dimensions": {
        "relevance": {"score": <0-10>, "feedback": "<explanation>", "suggestions": "<improvement tips>"},
        "accuracy": {"score": <0-10>, "feedback": "<explanation>", "suggestions": "<improvement tips>"},
        "completeness": {"score": <0-10>, "feedback": "<explanation>", "suggestions": "<improvement tips>"},
        "helpfulness": {"score": <0-10>, "feedback": "<explanation>", "suggestions": "<improvement tips>"}
    },
    "summary": "<overall assessment in 2-3 sentences>",
    "critical_issues": ["<issue 1>", "<issue 2>"] or []
}

Be objective, constructive, and specific in your feedback."""

    def _build_evaluation_prompt(
        self,
        user_query: str,
        agent_response: str,
        context: Optional[str],
        criteria: List[str]
    ) -> str:
        """
        Build the evaluation prompt for the judge LLM.
        
        Args:
            user_query: User's original query
            agent_response: Agent's response to evaluate
            context: Optional additional context
            criteria: List of evaluation criteria
        
        Returns:
            Formatted evaluation prompt
        """
        prompt = f"""Please evaluate the following agent response:

**User Query:**
{user_query}

**Agent Response:**
{agent_response}
"""
        
        if context:
            prompt += f"""
**Additional Context:**
{context}
"""
        
        prompt += f"""
**Evaluation Criteria:**
{', '.join(criteria)}

Please provide a detailed evaluation following the format specified in your system instructions."""
        
        return prompt
    
    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM's evaluation response.
        
        Args:
            response_text: Raw text response from judge LLM
        
        Returns:
            Parsed evaluation dictionary
        """
        try:
            # Try to extract JSON from response
            # Handle cases where LLM might wrap JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text.strip()
            
            evaluation = json.loads(json_str)
            evaluation["status"] = "success"
            return evaluation
            
        except json.JSONDecodeError:
            # If parsing fails, return raw response with error flag
            return {
                "status": "parse_error",
                "raw_response": response_text,
                "error": "Failed to parse JSON from LLM response"
            }
    
    def get_evaluation_summary(self, num_recent: int = 10) -> Dict[str, Any]:
        """
        Get summary statistics from recent evaluations.
        
        Args:
            num_recent: Number of recent evaluations to include
        
        Returns:
            Summary statistics dictionary
        """
        if not self.evaluation_history:
            return {"message": "No evaluations yet"}
        
        recent_evals = self.evaluation_history[-num_recent:]
        
        # Calculate average scores
        total_scores = []
        dimension_scores = {
            "relevance": [],
            "accuracy": [],
            "completeness": [],
            "helpfulness": []
        }
        
        for eval_result in recent_evals:
            if eval_result.get("status") == "success" and "overall_score" in eval_result:
                total_scores.append(eval_result["overall_score"])
                
                for dim in dimension_scores.keys():
                    if dim in eval_result.get("dimensions", {}):
                        dimension_scores[dim].append(
                            eval_result["dimensions"][dim].get("score", 0)
                        )
        
        summary = {
            "total_evaluations": len(self.evaluation_history),
            "recent_evaluations": len(recent_evals),
            "average_overall_score": sum(total_scores) / len(total_scores) if total_scores else 0,
            "dimension_averages": {
                dim: sum(scores) / len(scores) if scores else 0
                for dim, scores in dimension_scores.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def save_evaluation_history(self, filepath: str = "data/evaluation_history.json"):
        """
        Save evaluation history to a JSON file.
        
        Args:
            filepath: Path to save the evaluation history
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.evaluation_history, f, indent=2)
        
        print(f"✅ Evaluation history saved to {filepath}")
    
    def load_evaluation_history(self, filepath: str = "data/evaluation_history.json"):
        """
        Load evaluation history from a JSON file.
        
        Args:
            filepath: Path to load the evaluation history from
        """
        try:
            with open(filepath, 'r') as f:
                self.evaluation_history = json.load(f)
            print(f"✅ Loaded {len(self.evaluation_history)} evaluations from {filepath}")
        except FileNotFoundError:
            print(f"⚠️  No evaluation history found at {filepath}")
        except json.JSONDecodeError:
            print(f"❌ Error parsing evaluation history file")


def print_evaluation_report(evaluation: Dict[str, Any]):
    """
    Pretty print an evaluation report.
    
    Args:
        evaluation: Evaluation dictionary from LLMJudge.evaluate_response()
    """
    if evaluation.get("status") == "failed":
        print(f"❌ Evaluation failed: {evaluation.get('error')}")
        return
    
    print("\n" + "="*70)
    print("📊 LLM JUDGE EVALUATION REPORT")
    print("="*70)
    
    if "overall_score" in evaluation:
        print(f"\n🎯 Overall Score: {evaluation['overall_score']:.1f}/10")
    
    if "dimensions" in evaluation:
        print("\n📋 Dimension Scores:")
        for dim, details in evaluation["dimensions"].items():
            score = details.get("score", 0)
            emoji = "🟢" if score >= 8 else "🟡" if score >= 5 else "🔴"
            print(f"\n  {emoji} {dim.upper()}: {score}/10")
            print(f"     {details.get('feedback', 'N/A')}")
            if details.get("suggestions"):
                print(f"     💡 Suggestion: {details['suggestions']}")
    
    if "summary" in evaluation:
        print(f"\n📝 Summary:")
        print(f"   {evaluation['summary']}")
    
    if evaluation.get("critical_issues"):
        print(f"\n⚠️  Critical Issues:")
        for issue in evaluation["critical_issues"]:
            print(f"   • {issue}")
    
    print("\n" + "="*70 + "\n")


# Example usage
if __name__ == "__main__":
    # Initialize judge
    judge = LLMJudge()
    
    # Example evaluation
    user_query = "Get me options data for Apple in December 2025"
    agent_response = """I found 350 options contracts for AAPL expiring in December 2025. 
    The data includes both calls and puts with strike prices ranging from $150 to $250.
    Would you like me to export this to a CSV file or create a visualization?"""
    
    print("🔍 Evaluating agent response...")
    evaluation = judge.evaluate_response(user_query, agent_response)
    
    # Print report
    print_evaluation_report(evaluation)
    
    # Get summary
    summary = judge.get_evaluation_summary()
    print("📈 Evaluation Summary:")
    print(json.dumps(summary, indent=2))

