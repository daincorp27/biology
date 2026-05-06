"""
AI Pool Manager - Multi-Account Intelligent Token Balancing with E-Library Context Integration
Upgraded to use the modern google.genai SDK instead of the deprecated google.generativeai package.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import hashlib
from ai_pool_config import AI_POOL, GEMINI_KEYS_POOL

class AIPoolManager:
    """Manages rotating through multiple Gemini API accounts using the modern google.genai SDK"""
    
    def __init__(self):
        self.api_keys = GEMINI_KEYS_POOL
        self.settings = AI_POOL["settings"]
        
        # Track usage stats per unique API Key string
        self.key_metrics = defaultdict(lambda: {
            "requests_this_minute": 0,
            "minute_start_time": datetime.now(timezone.utc),
            "is_blocked_by_quota": False,
            "quota_block_time": None
        })
        
        self.model_cache = {} 
        self.current_key_index = 0
        self.last_error = None

    def _refresh_key_limits(self, key_str):
        """Resets request counters or clears expired quota blocks for a given key."""
        metrics = self.key_metrics[key_str]
        now = datetime.now(timezone.utc)
        
        if now - metrics["minute_start_time"] > timedelta(minutes=1):
            metrics["requests_this_minute"] = 0
            metrics["minute_start_time"] = now
            
        if metrics["is_blocked_by_quota"]:
            if metrics["quota_block_time"] and (now - metrics["quota_block_time"] > timedelta(minutes=5)):
                metrics["is_blocked_by_quota"] = False
                metrics["quota_block_time"] = None

    def get_active_api_key(self):
        """Traverses the account pool to return a clean, unblocked API key."""
        if not self.api_keys:
            return None
            
        total_keys = len(self.api_keys)
        keys_checked = 0
        
        while keys_checked < total_keys:
            candidate_key = self.api_keys[self.current_key_index]
            self._refresh_key_limits(candidate_key)
            metrics = self.key_metrics[candidate_key]
            
            if not metrics["is_blocked_by_quota"] and metrics["requests_this_minute"] < self.settings["requests_per_minute_limit"]:
                return candidate_key
                
            self.current_key_index = (self.current_key_index + 1) % total_keys
            keys_checked += 1
            
        return None

    def execute_gemini_call(self, api_key, prompt, catalog_context=""):
        """Queries Gemini using the new google.genai SDK structure with strict guardrails."""
        try:
            # UPGRADED: Import from the modern package and initialize an isolated client object
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            
            biology_guardrail = (
                "You are an advanced Biology specialist chatbot and E-Library academic guide called 'The Eagle AI'.\n"
                "Your objective is to provide accurate scientific information regarding Biology.\n\n"
                "Here is the list of available research books and materials in our E-Library database:\n"
                f"{catalog_context}\n\n"
                "RESPONSE INSTRUCTIONS:\n"
                "1. If one or more of the books listed above are highly relevant to the user's question, "
                "you MUST explicitly recommend that they check out that book by citing its EXACT title.\n"
                "2. If no books are directly related, answer the biological question directly using your internal knowledge.\n"
                "3. If a user asks about anything outside of Biology, you must politely decline.\n"
                "Keep responses professional, concise, factual, and refer to yourself as The Eagle AI."
            )

            # UPGRADED: The model execution API call syntax has changed to client.models.generate_content
            response = client.models.generate_content(
                model=self.settings["gemini_model"],
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=biology_guardrail,
                    max_output_tokens=400,
                    temperature=0.2
                )
            )
            
            if response and getattr(response, "text", None):
                self.key_metrics[api_key]["requests_this_minute"] += 1
                return response.text
                
        except Exception as e:
            err_msg = str(e).lower()
            print(f"Exception encountered on Account Key Index [{self.current_key_index}]: {str(e)}")
            
            if "429" in err_msg or "exhausted" in err_msg or "quota" in err_msg:
                print(f"Account index [{self.current_key_index}] exhausted. Tripping quota circuit-breaker.")
                self.key_metrics[api_key]["is_blocked_by_quota"] = True
                self.key_metrics[api_key]["quota_block_time"] = datetime.now(timezone.utc)
                
            self.last_error = f"Account key error: {str(e)}"
            
        return None

    def get_cache_key(self, query, catalog_context):
        hash_input = f"{query}_{catalog_context}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get_cached_response(self, query, catalog_context):
        if not self.settings["enable_caching"]:
            return None
        key = self.get_cache_key(query, catalog_context)
        if key in self.model_cache:
            cached = self.model_cache[key]
            if time.time() - cached["timestamp"] < self.settings["cache_ttl_seconds"]:
                return cached["response"]
            else:
                del self.model_cache[key]
        return None
    
    def cache_response(self, query, catalog_context, response):
        if not self.settings["enable_caching"] or not response:
            return
        key = self.get_cache_key(query, catalog_context)
        self.model_cache[key] = {"response": response, "timestamp": time.time()}

    def answer_question(self, query, catalog_context=""):
        cached = self.get_cached_response(query, catalog_context)
        if cached:
            return (cached, "cache", True)

        if not self.api_keys:
            self.last_error = "No API keys found in your GEMINI_KEYS_POOL configuration."
            return (None, None, False)

        active_key = self.get_active_api_key()
        
        if active_key:
            response = self.execute_gemini_call(active_key, query, catalog_context=catalog_context)
            if response:
                self.cache_response(query, catalog_context, response)
                return (response, f"gemini_account_{self.current_key_index + 1}", True)
                
            print("Active key encountered an error. Attempting hot-swap to backup key...")
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            backup_key = self.get_active_api_key()
            if backup_key and backup_key != active_key:
                response = self.execute_gemini_call(backup_key, query, catalog_context=catalog_context)
                if response:
                    self.cache_response(query, catalog_context, response)
                    return (response, f"gemini_account_{self.current_key_index + 1}", True)

        self.last_error = "All configured Gemini account keys are currently exhausted or blocked by rate limits."
        return (None, None, False)

    def get_pool_status(self):
        status = []
        for index, key in enumerate(self.api_keys):
            self._refresh_key_limits(key)
            metrics = self.key_metrics[key]
            masked_key = f"...{key[-6:]}" if len(key) > 6 else "Invalid Key"
            status.append({
                "account_index": index + 1,
                "key_ending": masked_key,
                "requests_this_minute": metrics["requests_this_minute"],
                "exhausted_status_flag": metrics["is_blocked_by_quota"]
            })
        return status

    def reset_pool(self):
        self.key_metrics.clear()
        self.model_cache.clear()
        self.current_key_index = 0


# Global singleton instance
ai_pool = AIPoolManager()