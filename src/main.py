"""Main application entry point - CLI mode."""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.logger import get_app_logger
from src.services.application_coordinator import ApplicationCoordinator


async def main_async():
    """Async main application entry point for CLI mode."""
    logger = get_app_logger()
    logger.info("Starting AGI Assistant (CLI mode)...")
    
    coordinator = None
    
    try:
        # Load configuration
        config = get_config()
        logger.info(f"Configuration loaded. Data directory: {config.data_dir}")
        
        # Ensure directories exist
        config.ensure_directories()
        logger.info("Data directories created")
        
        # Initialize and start application coordinator
        coordinator = ApplicationCoordinator()
        await coordinator.start()
        
        logger.info("AGI Assistant started successfully")
        print("AGI Assistant - Running")
        print(f"Data directory: {config.data_dir}")
        print(f"Log level: {config.log_level}")
        print(f"Session ID: {coordinator.get_current_session().id if coordinator.get_current_session() else 'None'}")
        print("\nCapture is active. Press Ctrl+Shift+P to pause/resume.")
        print("Press Ctrl+C to exit...")
        
        # Wait for shutdown signal
        await coordinator.wait_for_shutdown()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        print("\nShutting down gracefully...")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Error: {e}")
        
    finally:
        # Ensure coordinator is stopped
        if coordinator:
            await coordinator.stop()


def main():
    """Main application entry point."""
    try:
        # Run the async main function
        asyncio.run(main_async())
        
    except KeyboardInterrupt:
        print("\nApplication interrupted")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
