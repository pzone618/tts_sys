"""Engine manager for registering and managing TTS engines."""

from typing import Type

from loguru import logger

from packages.shared.enums import TTSEngine
from packages.shared.models import TTSRequest, Voice

from .circuit_breaker import circuit_breaker
from .engine_base import TTSEngineBase


class EngineManager:
    """Manages registration and lifecycle of TTS engines.
    
    Enhanced with fallback/degradation capabilities for high availability.
    """

    def __init__(self) -> None:
        """Initialize engine manager."""
        self._engines: dict[TTSEngine, TTSEngineBase] = {}
        self._engine_classes: dict[TTSEngine, Type[TTSEngineBase]] = {}
        
        # Categorize engines for fallback strategy
        self._online_engines: set[TTSEngine] = {
            TTSEngine.OPENAI,
            TTSEngine.AZURE,
            TTSEngine.GOOGLE,
            TTSEngine.YOUDAO,
        }
        self._offline_engines: set[TTSEngine] = {
            TTSEngine.EDGE,      # Can work offline with cache
            TTSEngine.PYTTSX3,   # Fully offline
        }

    def register_engine_class(
        self, engine_type: TTSEngine, engine_class: Type[TTSEngineBase]
    ) -> None:
        """Register an engine class (not yet instantiated).
        
        Args:
            engine_type: Engine type identifier
            engine_class: Engine class to register
        """
        self._engine_classes[engine_type] = engine_class
        logger.info(f"Registered engine class: {engine_type.value} -> {engine_class.__name__}")

    def initialize_engine(
        self, engine_type: TTSEngine, config: dict[str, str] | None = None
    ) -> None:
        """Initialize and register an engine instance.
        
        Args:
            engine_type: Engine type to initialize
            config: Engine configuration
        
        Raises:
            ValueError: If engine class not registered
        """
        if engine_type not in self._engine_classes:
            raise ValueError(f"Engine class not registered: {engine_type.value}")

        engine_class = self._engine_classes[engine_type]
        engine_instance = engine_class(config=config)
        self._engines[engine_type] = engine_instance
        logger.info(f"Initialized engine: {engine_type.value}")

    def get_engine(self, engine_type: TTSEngine) -> TTSEngineBase:
        """Get an engine instance.
        
        Args:
            engine_type: Engine type to retrieve
        
        Returns:
            Engine instance
        
        Raises:
            ValueError: If engine not found or not enabled
        """
        if engine_type not in self._engines:
            raise ValueError(f"Engine not initialized: {engine_type.value}")

        engine = self._engines[engine_type]
        if not engine.is_enabled():
            raise ValueError(f"Engine is disabled: {engine_type.value}")

        return engine

    def is_engine_available(self, engine_type: TTSEngine) -> bool:
        """Check if an engine is available and enabled.
        
        Args:
            engine_type: Engine type to check
        
        Returns:
            True if engine is available and enabled
        """
        return engine_type in self._engines and self._engines[engine_type].is_enabled()

    def get_available_engines(self) -> list[TTSEngine]:
        """Get list of available and enabled engines.
        
        Returns:
            List of engine types
        """
        return [
            engine_type
            for engine_type, engine in self._engines.items()
            if engine.is_enabled()
        ]

    async def get_all_voices(self, language: str | None = None) -> list[Voice]:
        """Get voices from all available engines.
        
        Args:
            language: Filter by language code
        
        Returns:
            Combined list of voices from all engines
        """
        all_voices: list[Voice] = []

        for engine_type in self.get_available_engines():
            try:
                engine = self.get_engine(engine_type)
                voices = await engine.get_voices(language)
                all_voices.extend(voices)
            except Exception as e:
                logger.error(f"Failed to get voices from {engine_type.value}: {e}")

        return all_voices

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all engines.
        
        Returns:
            Dictionary mapping engine names to health status
        """
        health_status = {}

        for engine_type, engine in self._engines.items():
            try:
                is_healthy = await engine.health_check()
                health_status[engine_type.value] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {engine_type.value}: {e}")
                health_status[engine_type.value] = False

        return health_status

    def enable_engine(self, engine_type: TTSEngine) -> None:
        """Enable an engine.
        
        Args:
            engine_type: Engine to enable
        
        Raises:
            ValueError: If engine not found
        """
        if engine_type not in self._engines:
            raise ValueError(f"Engine not found: {engine_type.value}")

        self._engines[engine_type].enable()
        logger.info(f"Enabled engine: {engine_type.value}")

    def disable_engine(self, engine_type: TTSEngine) -> None:
        """Disable an engine.
        
        Args:
            engine_type: Engine to disable
        
        Raises:
            ValueError: If engine not found
        """
        if engine_type not in self._engines:
            raise ValueError(f"Engine not found: {engine_type.value}")

        self._engines[engine_type].disable()
        logger.info(f"Disabled engine: {engine_type.value}")

    def __repr__(self) -> str:
        """String representation."""
        available = len(self.get_available_engines())
        total = len(self._engines)
        return f"<EngineManager(available={available}, total={total})>"
    
    # ========== Fallback/Degradation Methods ==========
    
    def is_online_engine(self, engine_type: TTSEngine) -> bool:
        """Check if engine is an online/network-dependent engine.
        
        Args:
            engine_type: Engine to check
            
        Returns:
            True if engine requires network connectivity
        """
        return engine_type in self._online_engines
    
    def get_fallback_chain(
        self,
        primary_engine: TTSEngine,
        custom_fallbacks: list[TTSEngine] | None = None,
    ) -> list[TTSEngine]:
        """Get fallback chain for an engine.
        
        Strategy:
        1. Start with primary engine
        2. If custom_fallbacks provided, use those
        3. Otherwise use default strategy:
           - For online engines: try other online engines first
           - Then fallback to offline engines
        
        Args:
            primary_engine: Primary engine to use
            custom_fallbacks: Custom fallback engines (optional)
            
        Returns:
            Ordered list of engines to try (includes primary)
        """
        chain = [primary_engine]
        
        if custom_fallbacks:
            # Use custom fallback chain
            for engine in custom_fallbacks:
                if engine != primary_engine and self.is_engine_available(engine):
                    chain.append(engine)
        else:
            # Default fallback strategy
            # 1. If primary is online, try other online engines
            if self.is_online_engine(primary_engine):
                for engine in self._online_engines:
                    if engine != primary_engine and self.is_engine_available(engine):
                        chain.append(engine)
            
            # 2. Finally fallback to offline engines
            for engine in self._offline_engines:
                if engine != primary_engine and self.is_engine_available(engine):
                    chain.append(engine)
        
        return chain
    
    async def synthesize_with_fallback(
        self,
        request: TTSRequest,
    ) -> tuple[bytes, TTSEngine, bool]:
        """Synthesize with automatic fallback on failure.
        
        Tries engines in fallback chain order. Uses circuit breaker
        to skip engines known to be failing.
        
        Args:
            request: TTS request with fallback configuration
            
        Returns:
            Tuple of (audio_data, actual_engine_used, fallback_occurred)
            
        Raises:
            RuntimeError: If all engines in chain fail
        """
        # Determine if fallback is enabled
        enable_fallback = getattr(request, 'enable_auto_fallback', True)
        max_retries = getattr(request, 'max_retries', 2)
        custom_fallbacks = getattr(request, 'fallback_engines', None)
        
        # Get fallback chain
        if enable_fallback:
            fallback_chain = self.get_fallback_chain(request.engine, custom_fallbacks)
        else:
            fallback_chain = [request.engine]
        
        logger.info(
            f"Fallback chain for request: {[e.value for e in fallback_chain]}"
        )
        
        last_error = None
        used_fallback = False
        
        # Try each engine in the chain
        for i, engine_type in enumerate(fallback_chain):
            # Check circuit breaker
            if not circuit_breaker.is_available(engine_type.value):
                logger.warning(
                    f"Skipping {engine_type.value} - circuit breaker is OPEN"
                )
                continue
            
            if i > 0:
                used_fallback = True
                logger.info(
                    f"Falling back to {engine_type.value} "
                    f"(attempt {i+1}/{len(fallback_chain)})"
                )
            
            # Try this engine with retries
            for retry in range(max_retries + 1):
                try:
                    engine = self.get_engine(engine_type)
                    
                    # Modify request for fallback engine
                    modified_request = await self._prepare_request_for_engine(
                        request, engine_type
                    )
                    
                    # Synthesize
                    audio_data = await engine.synthesize(modified_request)
                    
                    # Record success in circuit breaker
                    circuit_breaker.record_success(engine_type.value)
                    
                    logger.info(
                        f"✓ Successfully synthesized with {engine_type.value} "
                        f"(fallback={used_fallback}, retry={retry}/{max_retries})"
                    )
                    
                    return audio_data, engine_type, used_fallback
                
                except Exception as e:
                    last_error = e
                    logger.error(
                        f"✗ Engine {engine_type.value} failed "
                        f"(retry {retry+1}/{max_retries+1}): {e}"
                    )
                    
                    # Record failure in circuit breaker
                    circuit_breaker.record_failure(engine_type.value)
                    
                    # Continue to next retry or next engine
                    if retry < max_retries:
                        continue
                    break
        
        # All engines failed
        error_msg = (
            f"All engines failed. Tried: {[e.value for e in fallback_chain]}. "
            f"Last error: {last_error}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def _prepare_request_for_engine(
        self,
        original_request: TTSRequest,
        target_engine: TTSEngine,
    ) -> TTSRequest:
        """Prepare request for a specific engine (handle voice mapping).
        
        Args:
            original_request: Original request
            target_engine: Target engine
            
        Returns:
            Modified request suitable for target engine
        """
        if original_request.engine == target_engine:
            return original_request
        
        # Create a copy with modified properties
        modified = original_request.model_copy(deep=True)
        modified.engine = target_engine
        
        # Map voice to target engine
        modified.voice = await self._map_voice_for_engine(
            original_request.voice,
            target_engine,
        )
        
        return modified
    
    async def _map_voice_for_engine(
        self,
        original_voice: str,
        target_engine: TTSEngine,
    ) -> str:
        """Map a voice to the target engine.
        
        Tries multiple strategies:
        1. Exact match by voice ID
        2. Match by language
        3. Use engine default
        
        Args:
            original_voice: Original voice ID
            target_engine: Target engine
            
        Returns:
            Mapped voice ID for target engine
        """
        try:
            engine = self.get_engine(target_engine)
            voices = await engine.get_voices()
            
            if not voices:
                return self._get_default_voice(target_engine)
            
            # Strategy 1: Exact match
            for voice in voices:
                if voice.id == original_voice:
                    logger.info(
                        f"Exact voice match for {target_engine.value}: {original_voice}"
                    )
                    return voice.id
            
            # Strategy 2: Language match
            # Extract language prefix (e.g., "en-US" -> ["en", "US"])
            voice_parts = original_voice.split("-")[:2]
            for voice in voices:
                lang_parts = voice.language.split("-")[:2]
                if voice_parts == lang_parts:
                    logger.info(
                        f"Language match for {target_engine.value}: "
                        f"{original_voice} -> {voice.id}"
                    )
                    return voice.id
            
            # Strategy 3: Use first available voice
            default = voices[0].id
            logger.info(
                f"Using default voice for {target_engine.value}: {default}"
            )
            return default
        
        except Exception as e:
            logger.warning(f"Voice mapping failed: {e}")
            return self._get_default_voice(target_engine)
    
    def _get_default_voice(self, engine_type: TTSEngine) -> str:
        """Get default voice for an engine.
        
        Args:
            engine_type: Engine type
            
        Returns:
            Default voice ID
        """
        defaults = {
            TTSEngine.EDGE: "en-US-JennyNeural",
            TTSEngine.OPENAI: "alloy",
            TTSEngine.YOUDAO: "0",
            TTSEngine.PYTTSX3: "default",
            TTSEngine.AZURE: "en-US-JennyNeural",
            TTSEngine.GOOGLE: "en-US-Standard-A",
        }
        return defaults.get(engine_type, "default")


# Global engine manager instance
engine_manager = EngineManager()
