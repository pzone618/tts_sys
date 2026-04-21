"""Example script demonstrating TTS fallback/degradation features.

This script shows:
1. Normal synthesis
2. Automatic fallback when primary engine fails
3. Custom fallback chain
4. Circuit breaker monitoring
"""

import asyncio
import httpx


API_BASE = "http://localhost:8000/api/v1"


async def normal_synthesis():
    """Example 1: Normal synthesis without fallback."""
    print("\n=== Example 1: Normal Synthesis ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/tts/generate",
            json={
                "text": "Hello, world! This is a test.",
                "engine": "edge",
                "voice": "en-US-JennyNeural",
                "format": "mp3",
            },
        )
        
        data = response.json()
        print(f"✓ Status: {data['status']}")
        print(f"✓ Audio URL: {data['audio_url']}")
        print(f"✓ Processing time: {data['processing_time_ms']:.1f}ms")
        print(f"✓ Cached: {data['cached']}")


async def automatic_fallback():
    """Example 2: Automatic fallback when primary fails."""
    print("\n=== Example 2: Automatic Fallback ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/tts/generate",
            json={
                "text": "Testing automatic fallback mechanism.",
                "engine": "openai",  # May fail if no API key
                "voice": "alloy",
                "enable_auto_fallback": True,
                "max_retries": 1,
            },
        )
        
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"✓ Status: {data['status']}")
        print(f"✓ Requested engine: {metadata.get('requested_engine', 'N/A')}")
        print(f"✓ Actual engine: {metadata.get('actual_engine', 'N/A')}")
        print(f"✓ Fallback occurred: {metadata.get('fallback_occurred', False)}")
        
        if metadata.get('fallback_occurred'):
            print("⚠️  Primary engine failed, fallback was used")


async def custom_fallback_chain():
    """Example 3: Custom fallback chain."""
    print("\n=== Example 3: Custom Fallback Chain ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/tts/generate",
            json={
                "text": "你好，世界！这是自定义降级链测试。",
                "engine": "openai",
                "voice": "alloy",
                "fallback_engines": ["youdao", "edge", "pyttsx3"],
                "max_retries": 0,  # Don't retry, fallback immediately
            },
        )
        
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"✓ Status: {data['status']}")
        print(f"✓ Fallback chain: openai -> youdao -> edge -> pyttsx3")
        print(f"✓ Engine used: {metadata.get('actual_engine', 'N/A')}")


async def circuit_breaker_status():
    """Example 4: Monitor circuit breaker status."""
    print("\n=== Example 4: Circuit Breaker Status ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/tts/circuit-breaker/status")
        data = response.json()
        
        print(f"✓ Available engines: {', '.join(data['available_engines'])}")
        print("\nCircuit Breaker States:")
        
        for engine, stats in data["circuit_breakers"].items():
            state = stats["state"]
            symbol = "🔴" if state == "open" else "🟢" if state == "closed" else "🟡"
            
            print(f"  {symbol} {engine}:")
            print(f"     State: {state}")
            print(f"     Failures: {stats['failure_count']}")
            print(f"     Successes: {stats['success_count']}")


async def reset_circuit_breaker():
    """Example 5: Manually reset a circuit breaker."""
    print("\n=== Example 5: Reset Circuit Breaker ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/tts/circuit-breaker/reset/openai"
        )
        
        data = response.json()
        print(f"✓ {data['message']}")


async def quality_with_fallback():
    """Example 6: High quality synthesis with fallback."""
    print("\n=== Example 6: Quality Control with Fallback ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/tts/generate",
            json={
                "text": "High quality audio with automatic fallback support.",
                "engine": "openai",
                "voice": "nova",
                "quality": "hd",  # Request HD quality
                "enable_auto_fallback": True,
            },
        )
        
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"✓ Status: {data['status']}")
        print(f"✓ Quality requested: hd")
        print(f"✓ Engine used: {metadata.get('actual_engine', 'N/A')}")
        print(f"✓ File size: {data['size_bytes'] / 1024:.1f} KB")
        
        if metadata.get('fallback_occurred'):
            print("⚠️  Note: Fallback engine may not support HD quality")


async def stress_test_fallback():
    """Example 7: Stress test fallback mechanism."""
    print("\n=== Example 7: Stress Test (Multiple Requests) ===")
    
    async with httpx.AsyncClient() as client:
        # Send multiple requests simultaneously
        tasks = []
        for i in range(5):
            task = client.post(
                f"{API_BASE}/tts/generate",
                json={
                    "text": f"Stress test message {i+1}",
                    "engine": "openai",
                    "voice": "alloy",
                    "enable_auto_fallback": True,
                },
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        fallback_count = 0
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"  ✗ Request {i+1}: Failed - {response}")
            else:
                data = response.json()
                metadata = data.get("metadata", {})
                success_count += 1
                
                if metadata.get("fallback_occurred"):
                    fallback_count += 1
                
                print(
                    f"  ✓ Request {i+1}: {metadata.get('actual_engine', 'N/A')} "
                    f"({'fallback' if metadata.get('fallback_occurred') else 'primary'})"
                )
        
        print(f"\n✓ Success rate: {success_count}/5")
        print(f"✓ Fallback count: {fallback_count}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("TTS System - Fallback & Degradation Examples")
    print("=" * 60)
    
    try:
        # Run examples
        await normal_synthesis()
        await automatic_fallback()
        await custom_fallback_chain()
        await circuit_breaker_status()
        # await reset_circuit_breaker()  # Uncomment if needed
        await quality_with_fallback()
        await stress_test_fallback()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed!")
        print("=" * 60)
        
    except httpx.ConnectError:
        print("\n❌ Error: Cannot connect to API server")
        print("   Please ensure the API is running:")
        print("   uv run uvicorn packages.api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
