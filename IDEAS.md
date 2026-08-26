Let's continue now with other some files from the benchnmark. 

1 /  implement a CLI interface to test easily other files; Introduce a YAML file to configure  common parameters, such as folders, the different LLM used (for the agent, for the summary and for the judge), etc. 

2/ Re-enable the read-file tool because we need the skill system 

3/ The project NanoIndex  achieve very good results on financebench, with a similar approach as our. One reason I guess is that they provide financial knowledge. So let create a finance skills. We could reused they knowledge compilation :  https://github.com/NanoNets/nanoindex/blob/main/nanoindex/knowledge/financial_kb.json  

4/ More generally, review the skills. The one on genai-graph should be quite generic, and mention to not use available read-file tools (grep, ...). 
The skills in the benchmark can include finance knowledge (possibly as reference, or in another skill - you choose ). 

4/ Mafin2.5 also used a similar approach. They evaluation is criteria are worth considering in introduces in our judge  :  https://github.com/VectifyAI/Mafin2.5-FinanceBench/blob/main/eval.py 

5/ Run the agent on 3 other files you select  (with many questions, different that 10K, ... ), and update the report or create a new one.

Think, Think, propose a plan, ask questions, suggest alternatives, ...





- need better 'docgraph cat' commmand -> section range, section separator 

- There' other financial doc than 10K and 100 K  : EArnings, Annual Report, 8K, 10Q, 
    -> Update skills

- No summaries -   cli docgraph toc f391da52bf0af1c2 --yaml 
    Does that has an impact ? Measure it

- Summaries or embeddings of section ? 

- cli trajectory view  don't work

-  cli trajectory list -> only run-id: expected grouping per session-id 

- cli-graph as a plugin of genai-tk ? More plugins ? (Prefect ? BAML ? DeerFlow ? ) 

- Test with Harbor ?   (need one DB per session  ? ) 

- Compare with NanoIndex, PageIndex, Mistral Agentic Search https://mistral.ai/news/agentic-search/
https://github.com/NanoNets/nanoindex 

  https://huggingface.co/datasets/databricks/officeqa 
  https://arxiv.org/abs/2603.08655 

- Utiliser https://github.com/NanoNets/nanoindex/blob/main/nanoindex/knowledge/financial_kb.json ? 


- Main (budget) Nassime (200 €) ; argument comparaison avec Mistral ...  


- better workflow to combine markdownieation with summary (+Glinner ? )
   -> Create a YAML file ?   or OKG ?  Of GrapgDB, then file
   extract entities ?  Linkk them to wikipedia / dbpedia / ...  ? 


   Gliner ?    https://github.com/neuml/gliner   ? https://github.com/Knowledgator/GLinker 
   or during summarization process ? 

Markdown -> Sections -> Summarization


https://github.com/VectifyAI/Mafin2.5-FinanceBench/blob/main/eval.py

