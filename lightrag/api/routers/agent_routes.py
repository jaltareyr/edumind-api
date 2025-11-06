"""
Agent-based educational content generation routes for LightRAG API.
"""

import logging
import asyncio
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from agents import Runner

from lightrag import LightRAG
from ..utils_api import get_combined_auth_dependency, get_rag
from ..agents.config import create_educational_content_workflow
from ..agents.tools import set_tool_context

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])


class ContentGenerationRequest(BaseModel):
    """Request model for agent-based content generation."""
    
    requirements: str = Field(
        ...,
        description="Natural language description of content requirements. Example: 'I want a PPT on topics in software design principles from the knowledge graph, complete with citation for students to refer for their exams.'",
        min_length=10,
    )
    
    include_pdf: bool = Field(
        default=True,
        description="Whether to generate PDF output"
    )
    
    include_ppt: bool = Field(
        default=True,
        description="Whether to generate PowerPoint presentation output"
    )
    
    output_dir: Optional[str] = Field(
        default=None,
        description="Custom output directory for generated files (defaults to './output')"
    )


class ContentGenerationResponse(BaseModel):
    """Response model for agent-based content generation."""
    
    status: str = Field(
        description="Status of the generation process"
    )
    
    message: str = Field(
        description="Human-readable message about the generation"
    )
    
    generated_files: list[str] = Field(
        default_factory=list,
        description="List of file paths for generated documents"
    )
    
    download_urls: list[str] = Field(
        default_factory=list,
        description="List of download URLs for generated files"
    )
    
    topics_covered: list[str] = Field(
        default_factory=list,
        description="List of topics that were covered in the generated content"
    )
    
    agent_trace_id: Optional[str] = Field(
        default=None,
        description="Trace ID for debugging the agent execution"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )


def create_agent_routes(api_key: str = None):
    combined_auth = get_combined_auth_dependency(api_key)
    
    @router.post(
        "/agent/generate",
        response_model=ContentGenerationResponse,
        dependencies=[Depends(combined_auth)]
    )
    async def generate_educational_content(
        request: ContentGenerationRequest,
        pair: LightRAG = Depends(get_rag),
    ) -> ContentGenerationResponse:
        """
        Generate educational content using AI agents and the knowledge graph.
        """
        try:
            # Unpack the RAG instance and doc manager
            rag, doc_manager = pair
            
            # Set up output directory - convert to absolute path to avoid duplication
            output_dir = Path(request.output_dir) if request.output_dir else Path("./output")
            output_dir = output_dir.resolve()  # Convert to absolute path
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up tool context with RAG instance and configuration
            tool_context = {
                "rag": rag,
                "output_dir": str(output_dir),
            }
            set_tool_context(tool_context)
            
            # Create the agent workflow
            workflow_agent = create_educational_content_workflow( 
                include_pdf=request.include_pdf,
                include_ppt=request.include_ppt,
            )
            
            # Run the agent workflow with optimized settings
            logger.info("Starting agent workflow execution...")
            
            # Calculate adaptive max_turns based on complexity
            # Estimate: 1 turn per topic + formatting + generation + buffer
            estimated_topics = len(request.requirements.split(',')) + 3  # rough estimate
            adaptive_max_turns = min(max(15, estimated_topics * 2), 40)  # between 15-40
            
            logger.info(f"Using adaptive max_turns: {adaptive_max_turns}")
            
            try:
                result = await Runner.run(
                    workflow_agent,
                    input=request.requirements,
                    max_turns=adaptive_max_turns,  # Adaptive based on request complexity
                )
            except Exception as runner_error:
                # Check if it's MaxTurnsExceeded
                error_name = type(runner_error).__name__
                if error_name == "MaxTurnsExceeded":
                    logger.warning(f"Max turns exceeded. Attempting to extract partial results...")
                    # Try to get partial results from the agent's last state
                    # The Runner should still have captured tool outputs even if it exceeded turns
                    try:
                        # Re-raise to let outer exception handler deal with it
                        # but log that we tried to get partial results
                        logger.info("Agent made progress before hitting turn limit. Check output directory for any generated files.")
                    except:
                        pass
                raise runner_error
            
            logger.info(f"Agent workflow completed. Final output type: {type(result.final_output)}")
            logger.info(f"Agent final output: {result.final_output}")
            
            # Log all attributes of result for debugging
            logger.info(f"Result attributes: {dir(result)}")
            if hasattr(result, 'messages'):
                logger.info(f"Messages count: {len(result.messages) if result.messages else 0}")
            
            # Parse the agent's output
            # The agent should return information about generated files
            final_output = str(result.final_output)
            
            # Extract file paths from the output
            # This is a simple implementation - the agent's output should contain file paths
            generated_files = []
            topics_covered = []
            
            # Try to extract structured information from the output
            # In a production system, you might want to use structured output from the agent
            import re
            file_pattern = r'(?:output/|\./)[\w\-_/]+\.(?:pdf|pptx)'
            found_files = re.findall(file_pattern, final_output)
            generated_files.extend(found_files)
            
            # Check if files were actually created
            verified_files = []
            download_urls = []
            for file_path in generated_files:
                abs_path = Path(file_path)
                if not abs_path.is_absolute():
                    abs_path = output_dir / file_path
                
                if abs_path.exists():
                    verified_files.append(str(abs_path))
                    # Create download URL with filename
                    filename = abs_path.name
                    download_url = f"/agent/download/{filename}"
                    download_urls.append(download_url)
                    logger.info(f"Verified generated file: {abs_path}")
            
            # Determine status
            if verified_files:
                status = "success"
                message = f"Successfully generated {len(verified_files)} document(s)"
            elif generated_files:
                status = "partial"
                message = "Agent completed but some files may not have been generated correctly"
            else:
                status = "completed"
                message = "Agent workflow completed. Check agent output for details."
            
            return ContentGenerationResponse(
                status=status,
                message=message,
                generated_files=verified_files or generated_files,
                download_urls=download_urls,
                topics_covered=topics_covered,
                agent_trace_id=getattr(result, 'trace_id', None),
            )
            
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}", exc_info=True)
            return ContentGenerationResponse(
                status="error",
                message="Content generation failed",
                error=str(e),
                generated_files=[],
                download_urls=[],
                topics_covered=[],
            )
    
    
    @router.get(
        "/agent/download/{filename}",
        summary="Download Generated File",
        description="Download a generated PDF or PowerPoint file.",
        dependencies=[Depends(combined_auth)]
    )
    async def download_generated_file(
        filename: str,
    ) -> FileResponse:
        """
        Download a generated file by filename.
        """
        try:
            # Security: Only allow alphanumeric, dots, dashes, underscores in filename
            import re
            if not re.match(r'^[\w\-\.]+\.(pdf|pptx)$', filename):
                raise HTTPException(status_code=400, detail="Invalid filename")
            
            # Look for file in output directory
            output_dir = Path("./output").resolve()
            file_path = output_dir / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            # Determine media type
            media_type = "application/pdf" if filename.endswith('.pdf') else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            
            return FileResponse(
                path=str(file_path),
                media_type=media_type,
                filename=filename,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @router.get(
        "/agent/status",
        summary="Get Agent System Status",
        description="Check if the agent system is properly configured and ready to use.",
    )
    async def get_agent_status(
        auth=Depends(lambda: combined_auth),
    ) -> Dict[str, Any]:
        """
        Get the status of the agent system.
        """
        try:
            # Check if agents library is available
            import agents
            
            # Check if OpenAI API key is configured
            import os
            has_api_key = bool(os.getenv("OPENAI_API_KEY"))
            
            return {
                "status": "operational" if has_api_key else "warning",
                "message": "Agent system is ready" if has_api_key else "OpenAI API key not configured",
                "agents_version": getattr(agents, "__version__", "unknown"),
                "has_openai_key": has_api_key,
                "available_features": {
                    "pdf_generation": True,
                    "ppt_generation": True,
                    "knowledge_graph_query": True,
                },
            }
        except ImportError as e:
            return {
                "status": "error",
                "message": f"Agent system not properly installed: {str(e)}",
                "available_features": {},
            }
    
    return router


# This line is removed as we now use the factory function
# router = create_agent_routes()
