import streamlit as st
import json
import os
from googleapiclient.discovery import build
import google.generativeai as genai

st.set_page_config(page_title="AI Use Case Generator")
st.title("🤖 AI & GenAI Use Case Generator")
st.write("Enter a company name or industry below to generate potential AI/GenAI use cases and resources.")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_ID"]
    GOOGLE_CSE_API_KEY = st.secrets["GOOGLE_CSE_API_KEY"]
except KeyError as e:
    st.error(f"Missing API key in Streamlit Secrets: {e}. Please configure your secrets.toml file.")
    st.stop() 
    

@st.cache_resource
def init_GoogleSearch_service(api_key):
    """Initializes and caches the Google Custom Search API service."""
    # print("Initializing Google Search Service...") 
    return build("customsearch", "v1", developerKey=api_key)

@st.cache_resource
def init_gemini_model(api_key):
    """Initializes and caches the Gemini Generative Model."""
    # print("Initializing Gemini Model...")
    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.5,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
    }
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

try:
    GoogleSearch_service = init_GoogleSearch_service(GOOGLE_CSE_API_KEY)
    model = init_gemini_model(GEMINI_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Google APIs. Check your API keys and ensure the services are enabled. Error: {e}")
    st.stop()


# --- Agent Functions (Paste your working functions here) ---

def perform_GoogleSearch(query, num_results=5):
    """Performs a Google search using the Custom Search API."""
    try:
        search_results = GoogleSearch_service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            num=num_results
        ).execute()
        return search_results.get('items', [])
    except Exception as e:
        st.error(f"Error during Google Search API call for query '{query}': {e}")
        return []

def research_agent(company_or_industry_name, search_tool, llm_model):
    """Agent 1: Researches the industry/company, key offerings, and focus areas."""
    st.info(f"Research Agent: Starting research for '{company_or_industry_name}'...")
    research_data = {
        "input_name": company_or_industry_name,
        "industry": None,
        "segment": None,
        "offerings": None,
        "strategic_focus": None,
        "search_results": []
    }

    queries = [
        f"{company_or_industry_name} industry sector",
        f"{company_or_industry_name} key products and services",
        f"{company_or_industry_name} strategic priorities focus areas",
        f"{company_or_industry_name} company profile"
    ]

    all_search_text = ""
    for query in queries:
        # st.text(f"  Searching for '{query}'...") # Use st.text for smaller log messages
        results = search_tool(query)
        research_data["search_results"].extend(results)

        for item in results:
             all_search_text += f"Title: {item.get('title', 'N/A')}\nSnippet: {item.get('snippet', 'N/A')}\nURL: {item.get('link', '#')}\n\n"

    if not all_search_text:
        # st.warning("Research Agent: No significant search results found. Cannot proceed with detailed analysis.")
        return None 
    
    prompt = f"""
    Analyze the following text snippets from web searches about "{company_or_industry_name}".
    Identify and extract the following information:
    1. The main industry sector (e.g., Automotive, Finance, Healthcare).
    2. The specific segment within that industry (e.g., Commercial Banking, Oncology, E-commerce).
    3. Key products, services, or offerings (as a list of strings).
    4. Strategic focus areas or priorities (as a list of strings, e.g., improving efficiency, customer experience, expansion).

    Provide the output *only* as a structured JSON format with the keys: "industry", "segment", "offerings", "strategic_focus".
    If information for a key is not found, use "N/A" or an empty list [] where appropriate (e.g., offerings: []). Do not include any other text, explanation, or markdown formatting (like ```json) outside the JSON object.

    --- Text Snippets ---
    {all_search_text[:7000]} # Limit text length slightly more conservatively for safety

    --- JSON Output ---
    """
    extracted_info_str = None
    # st.text("  Sending search snippets to LLM for extraction...")
    try:
        response = llm_model.generate_content(prompt)
        extracted_info_str = response.text.strip()
        # st.text("  Received response from LLM. Attempting to parse JSON.")

        try:
            extracted_info = json.loads(extracted_info_str)
            research_data.update(extracted_info)
            st.info("Research Agent: Successfully extracted information.")

        except json.JSONDecodeError as e:
            # st.warning(f"Research Agent: Failed initial parsing of JSON from LLM: {e}")
            # st.text(f"  LLM Output was:\n{extracted_info_str}") # Print raw output for debugging

            cleaned_info_str = extracted_info_str.strip()
            if cleaned_info_str.startswith('```json'): cleaned_info_str = cleaned_info_str[7:]
            if cleaned_info_str.endswith('```'): cleaned_info_str = cleaned_info_str[:-3]
            cleaned_info_str = cleaned_info_str.strip()

            try:
                extracted_info = json.loads(cleaned_info_str)
                research_data.update(extracted_info)
                st.info("Research Agent: Successfully parsed after cleaning markdown.")
            except json.JSONDecodeError as e2:
                # st.error(f"Research Agent: Still failed to parse JSON after cleaning: {e2}")
                # st.error("Research Agent: Could not extract structured information due to persistent parsing errors.")
                research_data['industry'] = "Extraction Failed (Parsing Error)"
                research_data['segment'] = "Extraction Failed (Parsing Error)"
                research_data['offerings'] = ["Extraction Failed (Parsing Error)"]
                research_data['strategic_focus'] = ["Extraction Failed (Parsing Error)"]

    except Exception as e:
        # st.error(f"Research Agent: Error during LLM interaction: {e}")
        research_data['industry'] = f"Error: {e}"
        research_data['segment'] = f"Error: {e}"
        research_data['offerings'] = [f"Error: {e}"]
        research_data['strategic_focus'] = [f"Error: {e}"]

    st.info("Research Agent: Finished ")
    # Ensure industry is a string, not None, for the skipping check in other agents
    if research_data.get('industry') is None:
        research_data['industry'] = "N/A" # Set explicitly if extraction failed entirely

    return research_data

def use_case_generation_agent(research_data, search_tool, llm_model):
    """Agent 2: Analyzes trends and generates relevant AI/GenAI use cases."""
    if not research_data or research_data.get("industry") in [None, "N/A"] or "Error" in research_data.get("industry", ""):
        # st.warning("\n--- Use Case Agent: Insufficient research data. Skipping. ---")
        return []

    industry = research_data.get("industry", "a general industry")
    segment = research_data.get("segment", industry)
    offerings = ", ".join(research_data.get("offerings") if isinstance(research_data.get("offerings"), list) and research_data.get("offerings") else ["various products/services"])
    focus_areas = ", ".join(research_data.get("strategic_focus") if isinstance(research_data.get("strategic_focus"), list) and research_data.get("strategic_focus") else ["improving operations and customer experience"])
    company_name = research_data.get("input_name", "The company")


    # st.info(f"\n--- Use Case Generation Agent: Analyzing trends and generating use cases for {company_name} ({industry}/{segment}) ---")

    trend_queries = [
        f"AI trends in {industry} sector",
        f"Generative AI applications {segment}",
        f"Machine Learning use cases {industry} operations",
        f"{industry} companies using AI for customer experience"
    ]

    trend_snippets = ""
    # st.text("  Starting trend searches...")
    for query in trend_queries:
        # st.text(f"  Searching trends for '{query}'...")
        results = search_tool(query, num_results=3)
        for item in results:
            trend_snippets += f"Title: {item.get('title', 'N/A')}\nSnippet: {item.get('snippet', 'N/A')}\nURL: {item.get('link', '#')}\n\n"

    hypothetical_insights = f"""
Based on recent reports from McKinsey and Deloitte on digital transformation in the {industry} sector:
- Companies are seeing significant ROI from AI in supply chain forecasting.
- GenAI is increasingly used for personalizing customer communication and support.
- ML models are improving fraud detection rates by over 30%.
- Automation of routine tasks using AI frees up employees for strategic work.
"""
    trend_snippets += hypothetical_insights
    # st.text("  Trend searches finished. Compiling prompt for LLM.")


    prompt = f"""
Based on the following research about "{company_name}", which is in the "{industry}" sector,
specifically the "{segment}" segment, offering products/services like "{offerings}",
and focusing strategically on areas like "{focus_areas}".

Also consider the following industry trends and insights regarding AI, ML, and Generative AI:
--- Industry Trends/Insights ---
{trend_snippets[:7000]} # Limit trend text

Propose a list of 5-10 relevant AI/ML/GenAI use cases for "{company_name}".
For each use case:
1. Give it a clear title.
2. Briefly describe the problem it solves or the opportunity it addresses.
3. Explain how AI/ML/GenAI is applied.
4. Mention the potential benefit (e.g., improve process X, enhance customer Y, boost operational efficiency Z).
5. Briefly mention *why* this use case is relevant to the company/industry context (link to their offerings, focus areas, or industry trends).

Provide the output *only* as a JSON list of objects, where each object has keys: "title", "description", "ai_application", "potential_benefit", "relevance". Do not include any other text, explanation, or markdown formatting (like ```json) outside the JSON array. If you cannot think of specific relevant use cases based on this information, return an empty JSON array [].

--- JSON Output ---
"""

    use_cases = []
    use_cases_str = None
    # st.text("  Sending prompt to LLM for use case generation...")
    try:
        response = llm_model.generate_content(prompt)
        use_cases_str = response.text.strip()
        # st.text("  Received response from LLM. Attempting to parse JSON.")

        try:
            use_cases = json.loads(use_cases_str)
            if not isinstance(use_cases, list):
                #  st.warning("Use Case Agent: Parsed JSON is not a list. Returning empty list.")
                 use_cases = []
            # st.info(f"Use Case Agent: Generated {len(use_cases)} potential use cases.")

        except json.JSONDecodeError as e:
            # st.warning(f"Use Case Agent: Failed initial parsing of JSON from LLM: {e}")
            # st.text(f"  LLM Output was:\n{use_cases_str}")

            cleaned_use_cases_str = use_cases_str.strip()
            if cleaned_use_cases_str.startswith('```json'): cleaned_use_cases_str = cleaned_use_cases_str[7:]
            if cleaned_use_cases_str.endswith('```'): cleaned_use_cases_str = cleaned_use_cases_str[:-3]
            cleaned_use_cases_str = cleaned_use_cases_str.strip()

            start_index = cleaned_use_cases_str.find('[')
            end_index = cleaned_use_cases_str.rfind(']')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_array_str = cleaned_use_cases_str[start_index : end_index + 1]
                # st.text(f"  Found potential JSON array substring: {json_array_str[:500]}...")
                try:
                    use_cases = json.loads(json_array_str)
                    if not isinstance(use_cases, list):
                        # st.warning("Use Case Agent: Parsed JSON substring is not a list. Returning empty list.")
                        use_cases = []
                    st.info(f"Use Case Agent: Successfully parsed {len(use_cases)} use cases after cleaning and extracting.")
                except json.JSONDecodeError as e2:
                    # st.error(f"Use Case Agent: Still failed to parse JSON after cleaning and extracting: {e2}")
                    # st.error("Use Case Agent: Could not extract use cases due to persistent parsing errors.")
                    use_cases = []
            else:
                #  st.warning("Use Case Agent: Could not find a potential JSON array in the LLM output.")
                 use_cases = []

    except Exception as e:
        # st.error(f"Use Case Agent: Error during LLM use case generation: {e}")
        use_cases = []

    st.info("--- Use Case Generation Agent: Finished ---")
    return use_cases


def resource_collection_agent(use_cases, search_tool, llm_model):
    """Agent 3: Collects relevant dataset and resource links for the use cases."""
    if not use_cases:
        # st.warning("\n--- Resource Collection Agent: No use cases provided. Skipping. ---")
        return {}

    st.info("\n Resource Collection Agent: Collecting resources")
    collected_links = {}

    # We will generate queries based on use case titles
    # st.text("  Generating resource search queries based on use cases...")
    # The actual search and collection loop happens per use case below

    for uc in use_cases:
        title = uc.get("title", "Untitled Use Case")
        collected_links[title] = []
        # st.text(f"  Searching resources for '{title}'...")

        # Use targeted search queries for this specific use case title
        queries_for_uc = [
             f"{title} dataset site:kaggle.com OR site:huggingface.co/datasets OR site:github.com",
             f"{title} github code OR example site:github.com"
        ]

        for query in queries_for_uc:
             results = search_tool(query, num_results=2) # Get fewer results per query here
             for item in results:
                  link = item.get('link')
                  snippet = item.get('snippet', 'N/A')
                  if link and link not in [l['link'] for l in collected_links[title]]: # Avoid duplicates for the same use case
                       collected_links[title].append({"title": item.get('title', 'No Title'), "link": link, "snippet": snippet})
                    #    st.text(f"    Found: {item.get('title', 'No Title')}") # Shorter print for UI


    st.info("Resource Collection Agent: Finished")
    return collected_links


def optional_genai_proposer_agent(research_data, llm_model):
    """Optional Agent: Suggests general GenAI solutions (chatbots, report generation, etc.)."""
    if not research_data or research_data.get("industry") in [None, "N/A"] or "Error" in research_data.get("industry", ""):
        st.warning("\n--- Optional GenAI Proposer: Insufficient research data. Skipping. ---")
        return [] # Return empty list if research data is insufficient


    industry = research_data.get("industry", "a general industry")
    segment = research_data.get("segment", industry)
    offerings = ", ".join(research_data.get("offerings") if isinstance(research_data.get("offerings"), list) and research_data.get("offerings") else ["various products/services"])
    focus_areas = ", ".join(research_data.get("strategic_focus") if isinstance(research_data.get("strategic_focus"), list) and research_data.get("strategic_focus") else ["improving operations and customer experience"])
    company_name = research_data.get("input_name", "The company")


    # st.info(f"\n--- Optional GenAI Proposer: Suggesting general GenAI solutions for {company_name} ({industry}/{segment}) ---")

    prompt = f"""
Considering "{company_name}" in the "{industry}" sector, particularly the "{segment}" segment,
with offerings like "{offerings}" and focusing on "{focus_areas}".

Propose potential applications for general-purpose Generative AI solutions within this context.
Think about solutions like:
- AI-powered internal document search or knowledge base chatbots.
- Automated report generation or summarization (e.g., market reports, performance summaries).
- AI-powered customer support chatbots or virtual assistants.
- Automated content creation (e.g., marketing copy, product descriptions).

Provide the output *only* as a JSON list of objects, where each object has keys: "title", "application", "potential_benefit", "fit_area". Do not include any other text, explanation, or markdown formatting (like ```json) outside the JSON array.
If you cannot think of specific suggestions relevant to this context, return an empty JSON array [].

--- JSON Output ---
"""

    suggestions = []
    suggestions_str = None
    st.text("  Sending prompt to LLM for suggestions...")
    try: # Outer try block
        response = llm_model.generate_content(prompt)
        suggestions_str = response.text.strip()
        st.text("  Received response from LLM. Attempting to parse JSON.")

        try: # Inner try block for parsing
            suggestions = json.loads(suggestions_str)
            if not isinstance(suggestions, list):
                #  st.warning("Optional GenAI Proposer: Parsed JSON is not a list. Returning empty list.")
                 suggestions = []
            # st.info(f"Optional GenAI Proposer: Generated {len(suggestions)} suggestions.")

        except json.JSONDecodeError as e: # Catch parsing errors
            # st.warning(f"Optional GenAI Proposer: Failed initial parsing of JSON from LLM: {e}")
            # st.text(f"  LLM Output was:\n{suggestions_str}")

            # Robust parsing attempt
            cleaned_suggestions_str = suggestions_str.strip()
            if cleaned_suggestions_str.startswith('```json'): cleaned_suggestions_str = cleaned_suggestions_str[7:]
            if cleaned_suggestions_str.endswith('```'): cleaned_suggestions_str = cleaned_suggestions_str[:-3]
            cleaned_suggestions_str = cleaned_suggestions_str.strip()

            start_index = cleaned_suggestions_str.find('[')
            end_index = cleaned_suggestions_str.rfind(']')

            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_array_str = cleaned_suggestions_str[start_index : end_index + 1]
                # st.text(f"  Found potential JSON array substring: {json_array_str[:500]}...")
                try:
                    suggestions = json.loads(json_array_str)
                    if not isinstance(suggestions, list):
                        #  st.warning("Optional GenAI Proposer: Parsed JSON substring is not a list. Returning empty list.")
                         suggestions = []
                    # st.info(f"Optional GenAI Proposer: Successfully parsed {len(suggestions)} suggestions after cleaning and extracting.")
                except json.JSONDecodeError as e2:
                    # st.error(f"Optional GenAI Proposer: Still failed to parse JSON after cleaning and extracting: {e2}")
                    # st.error("Optional GenAI Proposer: Could not extract suggestions due to persistent parsing errors.")
                    suggestions = []
            else:
                #  st.warning("Optional GenAI Proposer: Could not find a potential JSON array in the LLM output.")
                 suggestions = []


    except Exception as e: # Catch general LLM errors
        st.error(f"Optional GenAI Proposer: Error during LLM suggestion generation: {e}")
        suggestions = []

    # --- Add fallback suggestion if the list is empty AFTER LLM attempt ---
    if not suggestions:
        st.info("Optional GenAI Proposer: No specific suggestions found by LLM, adding a generic fallback.")
        suggestions = [{
            "title": "Generic AI-Powered Chatbot for FAQs",
            "application": "Implement a chatbot on the company website or internal portal to answer frequently asked questions.",
            "potential_benefit": "Improve efficiency by automating responses to common queries, free up staff time, provide 24/7 support.",
            "fit_area": "Customer Service, Internal Operations, HR"
        }]
    # --- End of fallback ---


    st.info("--- Optional GenAI Proposer: Finished ---")
    return suggestions


def orchestrator(company_or_industry_name, search_tool, llm_model):
    """Manages the workflow between the agents."""
    st.header(f"Generating Proposal for {company_or_industry_name}")
    with st.spinner("Running Research Agent..."):
        research_output = research_agent(company_or_industry_name, search_tool, llm_model)

    if not research_output or research_output.get("industry") in [None, "N/A"] or "Error" in research_output.get("industry", ""):
        st.error("Orchestrator: Research failed or returned insufficient data. Cannot generate use cases.")
        return {
            "use_cases": [],
            "resource_links": {},
            "genai_suggestions": [],
            "research_data": research_output,
            "status": "Failed Research"
        }

    with st.spinner("Running Use Case Generation Agent..."):
        use_cases = use_case_generation_agent(research_output, search_tool, llm_model)

    with st.spinner("Running Resource Collection Agent..."):
        resource_links = resource_collection_agent(use_cases, search_tool, llm_model)

    with st.spinner("Running Optional GenAI Proposer Agent..."):
        genai_suggestions = optional_genai_proposer_agent(research_output, llm_model)

    st.success("Orchestrator: Process Finished.")

    return {
        "use_cases": use_cases,
        "resource_links": resource_links,
        "genai_suggestions": genai_suggestions,
        "research_data": research_output,
        "status": "Success"
    }
# ... (previous code) ...

# --- Streamlit UI Elements and Logic ---

company_or_industry_input = st.text_input("Enter Company Name or Industry", "")

if st.button("Generate Use Cases"):
    if not company_or_industry_input:
        st.warning("Please enter a company name or industry.")
    else:
        # Use a top-level spinner for the whole process
        with st.spinner("Running AI Agents... This may take a moment."):
            results = orchestrator(company_or_industry_input, perform_GoogleSearch, model)

        # --- Display Results ---
        st.markdown("---") # Separator

        if results["status"] == "Failed Research":
            st.error("Could not generate a proposal due to initial research failure.")
            st.subheader("Research Attempt Summary:")
            # Display limited research data even on failure
            st.write(f"**Industry:** {results['research_data'].get('industry', 'N/A')}")
            st.write(f"**Segment:** {results['research_data'].get('segment', 'N/A')}")
            # Use helper function for lists to handle potential non-list types from failed extraction
            st.write(f"**Key Offerings:** {', '.join([item for item in results['research_data'].get('offerings', ['N/A']) if isinstance(item, str)])}")
            st.write(f"**Strategic Focus:** {', '.join([item for item in results['research_data'].get('strategic_focus', ['N/A']) if isinstance(item, str)])}")


        else: # Status is Success
            st.subheader("Research Summary")
             # Use helper function for lists to handle potential non-list types from failed extraction
            st.write(f"**Industry:** {results['research_data'].get('industry', 'N/A')}")
            st.write(f"**Segment:** {results['research_data'].get('segment', 'N/A')}")
            st.write(f"**Key Offerings:** {', '.join([item for item in results['research_data'].get('offerings', ['N/A']) if isinstance(item, str)])}")
            st.write(f"**Strategic Focus:** {', '.join([item for item in results['research_data'].get('strategic_focus', ['N/A']) if isinstance(item, str)])}")


            st.subheader("Proposed AI/GenAI Use Cases")
            if results["use_cases"]:
                for i, uc in enumerate(results["use_cases"]):
                    st.markdown(f"**{i+1}. {uc.get('title', 'Untitled Use Case')}**")
                    st.write(f"**Description:** {uc.get('description', 'N/A')}")
                    st.write(f"**AI Application:** {uc.get('ai_application', 'N/A')}")
                    st.write(f"**Potential Benefit:** {uc.get('potential_benefit', 'N/A')}")
                    st.write(f"**Relevance:** {uc.get('relevance', 'N/A')}")
                    st.write("---") # Separator for use cases

                st.subheader("Relevant Resource Assets")
                # --- Logic to display and prepare download file for Resource Links ---
                resource_file_content = "# Relevant Resource Links\n\n"
                file_name_base = results['research_data'].get('input_name', 'resources').replace(' ', '_').replace('/', '_') # Basic sanitization
                file_name = f"{file_name_base}_ai_resources.md"

                all_links_found = False # Flag to check if any links were actually collected
                if results["resource_links"]:
                    # Iterate through use cases to display resources under each one
                    for use_case_title, links in results["resource_links"].items():
                        if links: # Check if the list of links for this use case is not empty
                            all_links_found = True
                            st.markdown(f"**Resources for: {use_case_title}**")
                            resource_file_content += f"## {use_case_title}\n\n" # Add to file content

                            for res in links:
                                link_text = res.get('title', res.get('link', 'Link')) # Use title if available, otherwise link, otherwise default
                                link_url = res.get('link', '#')
                                # Display link in Streamlit UI
                                st.markdown(f"- [{link_text}]({link_url})")
                                # Add link to file content (use standard markdown format)
                                resource_file_content += f"- [{link_text}]({link_url})\n"

                            st.text("") # Add a small space in UI after resources for a use case
                            resource_file_content += "\n" # Add a small space in file content

                if all_links_found: # Only show button if there's content to download
                    resource_bytes = resource_file_content.encode('utf-8')
                    st.download_button(
                        label="Download Resource Links (.md)",
                        data=resource_bytes,
                        file_name=file_name,
                        mime="text/markdown"
                    )
                else:
                    st.write("No specific resource links found for the generated use cases.") # Message if dictionary was empty or all link lists were empty


            else: # This happens if results["resource_links"] is empty
                st.write("No resource links collected (either no use cases generated or search failed).")


            st.subheader("General GenAI Solution Suggestions")
            # This section will now *always* show something if the agent didn't skip
            if results["genai_suggestions"]:
                 for i, suggestion in enumerate(results["genai_suggestions"]):
                      st.markdown(f"**{i+1}. {suggestion.get('title', 'Untitled Suggestion')}**")
                      st.write(f"**Application:** {suggestion.get('application', 'N/A')}")
                      st.write(f"**Potential Benefit:** {suggestion.get('potential_benefit', 'N/A')}")
                      st.write(f"**Fit Area:** {suggestion.get('fit_area', 'N/A')}")
                      st.text("") # Small space
            else:
                 # This fallback message should ideally not be hit now due to the agent's fallback
                 st.write("No general GenAI solution suggestions found (this is unexpected).")


        st.markdown("---") # Final Separator
        st.success("Proposal Generation Complete.")