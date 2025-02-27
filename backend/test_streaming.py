import asyncio
import httpx

# REPLACE WITH YOUR OWN REPORT ID
YOUR_REPORT_ID = 107

url = f"http://localhost/oracle/update_report_thinking_status?report_id={YOUR_REPORT_ID}"
headers = {
    "X-Auth-Token": "4adaf64ff68cd84fb8f3aa6366812cb8aa20a8cd8d1abd156d15d578bea6680a",
}

async def test_async_stream():
    # Create an asynchronous HTTP client
    async with httpx.AsyncClient(timeout=600) as client:
        # Open a stream to the SSE endpoint
        async with client.stream("GET", url, headers=headers) as response:
            # Iterate over the response as lines of text
            async for line in response.aiter_lines():
                # SSE sends empty lines to separate events, so you might want to ignore them
                if line.strip():
                    print("Received:", line)

# Run the asynchronous test function
if __name__ == '__main__':
    asyncio.run(test_async_stream())