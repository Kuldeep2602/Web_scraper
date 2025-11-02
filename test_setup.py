"""
Simple test script to verify installation and connectivity.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_connectivity():
    """Test connection to Jira API."""
    print("Testing Jira API connectivity...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = "https://issues.apache.org/jira/rest/api/2/project/KAFKA"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ Successfully connected to Jira API")
                    print(f"✓ Test project: {data.get('name', 'Unknown')}")
                    return True
                else:
                    print(f"✗ API returned status code: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False


def test_imports():
    """Test that all required modules can be imported."""
    print("\nTesting module imports...")
    
    modules = [
        ("asyncio", "asyncio"),
        ("aiohttp", "aiohttp"),
        ("requests", "requests"),
        ("tenacity", "tenacity"),
        ("tqdm", "tqdm"),
        ("dotenv", "python-dotenv"),
    ]
    
    success = True
    
    for module_name, package_name in modules:
        try:
            __import__(module_name)
            print(f"✓ {package_name}")
        except ImportError:
            print(f"✗ {package_name} not installed")
            success = False
    
    return success


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config import Config
        
        Config.ensure_directories()
        
        print(f"✓ Configuration loaded")
        print(f"✓ Projects: {', '.join(Config.JIRA_PROJECTS)}")
        print(f"✓ Rate limit: {Config.RATE_LIMIT} req/s")
        print(f"✓ Output directory: {Config.OUTPUT_DIR}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {str(e)}")
        return False


def test_directories():
    """Test that required directories exist."""
    print("\nTesting directory structure...")
    
    directories = [
        Path("src"),
        Path("output"),
        Path("state"),
    ]
    
    success = True
    
    for directory in directories:
        if directory.exists():
            print(f"✓ {directory}")
        else:
            print(f"✗ {directory} not found")
            success = False
    
    return success


async def test_api_client():
    """Test API client functionality."""
    print("\nTesting API client...")
    
    try:
        from src.config import Config
        from src.logger import setup_logger
        from src.api_client import JiraAPIClient
        
        logger = setup_logger(level="WARNING")
        
        async with JiraAPIClient(Config, logger) as api_client:
            # Test project info
            project_info = await api_client.get_project_info("KAFKA")
            
            if project_info and "name" in project_info:
                print(f"✓ API client working")
                print(f"✓ Retrieved project: {project_info['name']}")
                
                # Test search
                result = await api_client.search_issues(
                    jql="project = KAFKA",
                    start_at=0,
                    max_results=1
                )
                
                if result and "total" in result:
                    print(f"✓ Search working (found {result['total']} issues)")
                    return True
                else:
                    print("✗ Search returned unexpected result")
                    return False
            else:
                print("✗ Failed to retrieve project info")
                return False
                
    except Exception as e:
        print(f"✗ API client error: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("JIRA SCRAPER - INSTALLATION TEST")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("Directory Structure", test_directories()))
    results.append(("Configuration", test_config()))
    results.append(("Network Connectivity", await test_connectivity()))
    results.append(("API Client", await test_api_client()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:30s} {status}")
    
    print("=" * 60)
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! You're ready to scrape.")
        print("\nRun: python run.py --projects ZOOKEEPER")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  1. Make sure virtual environment is activated")
        print("  2. Run: pip install -r requirements.txt")
        print("  3. Check internet connectivity")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
