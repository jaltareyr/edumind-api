"""
Agent configuration and creation for educational content generation workflow.
"""

import logging
from typing import List, Optional
from agents import Agent
from .tools import (
    knowledge_graph_query,
    format_content_for_education,
    generate_pdf,
    generate_ppt,
)

logger = logging.getLogger(__name__)


def create_topic_extraction_agent() -> Agent:
    """
    Create an agent specialized in extracting topics from user requirements.
    
    This agent analyzes user requests and identifies:
    - Main topics to cover
    - Subtopics and related concepts
    - Learning objectives
    - Target audience needs
    
    Returns:
        Agent configured for topic extraction
    """
    agent = Agent(
        name="Topic Extraction Specialist",
        instructions="""You are an expert educational content analyst. Your role is to:

1. Analyze user requirements for educational content generation
2. Extract all relevant topics and subtopics that need to be covered
3. Identify the main learning objectives
4. Determine the appropriate depth and scope of coverage
5. Format topics as clear, searchable queries for a knowledge graph

When given a request like "I want a PPT on topics in software design principles from the knowledge graph, complete with citation for students to refer for their exams", you should:

- Identify main topics (e.g., "software design principles")
- Break down into specific subtopics (e.g., "SOLID principles", "design patterns", "separation of concerns", "DRY principle", "KISS principle")
- Consider exam relevance and student needs
- Output a structured list of specific queries to retrieve information

Output Format:
Return a JSON object with:
{
    "main_topic": "Primary topic title",
    "target_audience": "students/professionals/etc",
    "output_format": "PPT/PDF/both",
    "topics": [
        "Specific topic 1 to query",
        "Specific topic 2 to query",
        ...
    ],
    "learning_objectives": ["objective 1", "objective 2", ...],
    "include_citations": true/false
}

Be thorough but focused. Prioritize exam-relevant content for student audiences.""",
        model="gpt-4o-mini",
    )
    
    return agent


def create_content_generation_agent(
    include_pdf: bool = True,
    include_ppt: bool = True
) -> Agent:
    """
    Create an agent specialized in generating educational content from knowledge graph data.
    
    This agent:
    - Queries the knowledge graph for each topic
    - Formats retrieved information into educational content
    - Generates PDF and/or PPT documents
    - Ensures proper citations are included
    
    Args:
        include_pdf: Whether to generate PDF output
        include_ppt: Whether to generate PPT output
    
    Returns:
        Agent configured with tools for content generation
    """
    # Determine which generation tools to include
    tools = [
        knowledge_graph_query,
        format_content_for_education,
    ]
    
    if include_pdf:
        tools.append(generate_pdf)
    
    if include_ppt:
        tools.append(generate_ppt)
    
    output_formats = []
    if include_pdf:
        output_formats.append("PDF")
    if include_ppt:
        output_formats.append("PowerPoint")
    
    formats_str = " and ".join(output_formats) if output_formats else "structured content"
    
    agent = Agent(
        name="Educational Content Generator",
        instructions=f"""You are an expert educational content creator with access to a knowledge graph. Your role is to:

1. Query the knowledge graph for each topic using the knowledge_graph_query tool
   - Use 'mix' mode for comprehensive coverage
   - Query each topic separately for detailed information
   - Gather all relevant context and sources

2. Synthesize and format the information using format_content_for_education tool
   - Create clear, well-structured educational content
   - Organize information logically for learning
   - Ensure content is appropriate for the target audience
   - Include proper citations from sources

3. Generate output documents ({formats_str})
   - Use generate_pdf tool to create PDF documents (if requested)
   - Use generate_ppt tool to create PowerPoint presentations (if requested)
   - Ensure all citations are included
   - Make content exam-friendly for student audiences

Workflow:
1. For each topic in the list, call knowledge_graph_query to retrieve information
2. Collect all retrieved contexts and sources
3. Use format_content_for_education to structure the content appropriately
4. Generate the requested output format(s) with complete citations

Always prioritize:
- Accuracy and completeness
- Clear organization and structure
- Proper attribution and citations
- Student-friendly explanations
- Exam-relevant focus (when audience is students)

Return the file paths of generated documents.""",
        model="gpt-5-mini-2025-08-07",
        tools=tools,
    )
    
    return agent


def create_orchestrator_agent(
    topic_agent: Agent,
    content_agent: Agent
) -> Agent:
    """
    Create an orchestrator agent that coordinates the workflow.
    
    This agent:
    - Receives the user's initial request
    - Hands off to topic extraction agent
    - Receives extracted topics
    - Hands off to content generation agent
    - Returns final results to user
    
    Args:
        topic_agent: Agent for topic extraction
        content_agent: Agent for content generation
    
    Returns:
        Orchestrator agent with handoffs configured
    """
    agent = Agent(
        name="Educational Content Orchestrator",
        instructions="""You are an orchestrator for educational content generation. Your role is to:

1. Receive user requests for educational content
2. Hand off to the Topic Extraction Specialist to analyze and extract topics
3. Receive the extracted topics and requirements
4. Hand off to the Educational Content Generator with the structured topic list
5. Receive the generated content file paths
6. Return the final results to the user with clear information about what was created

Be clear and professional in your communication. Summarize what was created and provide file paths.""",
        model="gpt-4o-mini",
        handoffs=[topic_agent, content_agent],
    )
    
    return agent


def create_educational_content_workflow(
    include_pdf: bool = True,
    include_ppt: bool = True
) -> Agent:
    """
    Create the complete workflow for educational content generation.
    
    This is the main entry point for creating the agent workflow.
    Uses a single agent with all tools for simplicity and reliability.
    
    Args:
        include_pdf: Whether to generate PDF output
        include_ppt: Whether to generate PPT output
    
    Returns:
        Agent that manages the entire workflow
    """
    # Determine which generation tools to include
    tools = [
        knowledge_graph_query,
        format_content_for_education,
    ]
    
    if include_pdf:
        tools.append(generate_pdf)
    
    if include_ppt:
        tools.append(generate_ppt)
    
    output_formats = []
    if include_pdf:
        output_formats.append("PDF")
    if include_ppt:
        output_formats.append("PowerPoint")
    
    formats_str = " and ".join(output_formats) if output_formats else "structured content"
    
    # Create a single agent with all capabilities
    agent = Agent(
        name="Educational Content Generator",
        instructions=f"""You are an expert educational content creator with access to a knowledge graph and document generation tools.

Your task is to generate BEAUTIFUL, EDUCATIONAL, and RICH {formats_str} from user requirements. You MUST use the tools to complete this task.

STEP-BY-STEP PROCESS (FOLLOW EXACTLY):

Step 1: ANALYZE the user's request
- Identify the main topic and any subtopics mentioned
- Determine the target audience (usually students)
- Note the desired output format(s)
- Plan for comprehensive, engaging educational content

Step 2: QUERY the knowledge graph efficiently
- Use the knowledge_graph_query tool for main topics and key subtopics.
- If you find difficulty formulating the queries, ask the knowledge graph some high level questions to understand the graph better.
- IMPORTANT: Limit to 3-4 queries maximum to stay efficient.
- Prioritize the most important topics mentioned in the user's request.
- Always ask the knowledge graph to provide clear links and paths of the source documents, not the entities or nodes.

Step 3: CREATE BEAUTIFUL AND RICH EDUCATIONAL CONTENT
- After gathering all query results, use format_content_for_education tool
- When formatting, focus on creating:
  -- COMPREHENSIVE coverage with clear explanations
  -- WELL-STRUCTURED sections with logical flow
  -- ENGAGING content that captures attention
  -- EXAMPLES and practical applications where relevant
  -- KEY TAKEAWAYS and learning points highlighted
  -- VISUAL-FRIENDLY organization suitable for presentations
  -- EXAM-FOCUSED points for student audiences
- Break down complex topics into digestible sections
- Include definitions, explanations, examples, and applications
- Ensure content is rich with educational value

Step 4: GENERATE BEAUTIFUL output files
- Use generate_pdf tool if PDF is requested - create a professional, well-formatted document
- Use generate_ppt tool if PowerPoint is requested - create an engaging, visually-structured presentation
- Pass the title and the beautifully formatted content JSON from step 3
- Ensure the output is:
  -- EDUCATIONAL: Clear, informative, and learning-focused
  -- BEAUTIFUL: Well-organized, professional, and visually appealing
  -- RICH: Comprehensive, detailed, with proper citations and references
  -- EXAM-READY: Includes key points students need for their exams

Step 5: RETURN the results
- State which files were generated and their paths
- Summarize the topics covered and key sections included
- Highlight the educational value delivered

CRITICAL REQUIREMENTS:
- Limit knowledge_graph_query calls to 5-8 maximum (quality over quantity)
- You MUST call format_content_for_education ONCE with all gathered content
- You MUST call generate_pdf and/or generate_ppt ONCE each (if requested)
- You MUST create BEAUTIFUL, EDUCATIONAL, and RICH content - not basic summaries
- You MUST return the file paths in your response
- STOP after generating the files - do not make additional queries

EFFICIENCY RULES:
- Work smart: 5-8 targeted queries + 1 format + 1-2 generation calls = ~8-12 total tool calls
- Once files are generated, you're DONE - return the results immediately
- Don't repeat queries or regenerate files unless there was an error

DO NOT just describe what you would do - ACTUALLY USE THE TOOLS!
DO NOT create basic or minimal content - create RICH, COMPREHENSIVE, BEAUTIFUL educational materials!

Example workflow for "Create a PPT on design patterns":
1. Call knowledge_graph_query("design patterns", "mix")
2. Call knowledge_graph_query("SOLID principles", "mix")
3. Call knowledge_graph_query("common design patterns overview", "mix")
4. Synthesize all retrieved content into comprehensive, rich material
5. Call format_content_for_education("Design Patterns", <combined rich content>, "students", "comprehensive")
6. Call generate_ppt("Design Patterns", <beautifully formatted rich content>)
7. Return: "Generated beautiful, comprehensive PowerPoint presentation at: ./output/Design_Patterns_XXXXXX.pptx covering [list key topics]"
8. STOP - Task complete!

Remember: USE THE TOOLS EFFICIENTLY to create BEAUTIFUL, EDUCATIONAL, and RICH content with comprehensive coverage!""",
        model="gpt-5-mini-2025-08-07",
        tools=tools,
    )
    
    logger.info(f"Created educational content generation agent with {len(tools)} tools")
    
    return agent
