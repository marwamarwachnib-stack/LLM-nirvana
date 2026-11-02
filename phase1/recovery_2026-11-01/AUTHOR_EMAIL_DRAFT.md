# Email to the paper's authors (draft, NOT sent)

**Status.** Draft for Marwa Chnib to review and send herself after approval. Nothing has been sent. It supersedes `phase1/AUTHOR_DATA_REQUEST.md` (uncommitted, left unchanged) with the findings of 2026-11-01.

- **To:** the corresponding author of Bhatia et al. (2024). Take the address from the published paper; not filled in here.
- **Cc:** Prof. [supervisor].

**Correction to the requested topic "the missing Small Cat 1 module".** The repository has one Cat 1 program **more** than the paper (21 vs 20), and one Cat 2 program **fewer** (19 vs 20). Table 1's Cat 2 mean fits 19 programs. So point 2 asks about the composition, not about a missing Cat 1 file.

---

**Subject:** Data request for a replication of "Unit Test Generation using Generative AI" (LLM4Code 2024)

Dear Shreya Bhatia, Tarushi Gandhi, Dhruv Kumar and Pankaj Jalote,

I am a PhD student at [university], working with Prof. [supervisor] on large language models for automated program debugging. I am replicating your LLM4Code 2024 paper "Unit Test Generation using Generative AI: A Comparative Performance Analysis of Autogeneration Tools" (DOI 10.1145/3643795.3648396), with open local language models alongside Pynguin.

Your public repository (github.com/Rey-2001/LLM-nirvana) has been very valuable: with your stored suites and coverage commands, we reproduce all 77 of your stored small-set coverage reports exactly, and 223 of 237 reports overall. A few items are not in the repository, and we could not find them elsewhere. I would be very grateful for your help with these:

1. **The six large Category 1 modules (100–300 LOC)** used in Section 2.2 and Table 3.
   - Could you share them, or their original sources (repository URLs and file paths)?
   - Is `100_300 LOC p1/cat1/s15/example.py` one of the six?
   - Did they come from the Lukasczyk et al. benchmark (as Section 2.2 suggests for the large modules) or from GitHub projects like s15?
   - Are the six in Section 2.2 the same six as in Table 3?
   - Section 2.2 mentions 49 projects from the benchmark, while the 43 p2 modules come from 11 PyPI packages. Should we read "project" as "module" there?

2. **The composition of the small set.**
   - The `0_100 LOC` folder holds 21 Category 1 and 19 Category 2 programs, while the paper reports 20 per category.
   - Which Category 1 program was left out of Table 1?
   - Was a 20th Category 2 program used that is not in the repository?

3. **Compilation reports.** In `100_300 LOC p2/ChatGPT coverage`, samples 1, 2, 7 and 10 have no `compilation_report.txt`. Could you share them, if they exist?

4. **The original ChatGPT outputs and experimental data:**
   - the ChatGPT test suites and coverage reports for the 60 small programs, including the refactored Category 1 modules (Table 1);
   - the test suite and coverage of each improvement iteration for the p1 modules and the large Category 1 modules (Table 3, Figure 6);
   - the ChatGPT coverage reports of p2 samples 8 and 10;
   - the data behind Table 4, and which dataset it uses;
   - the ChatGPT version and dates, and whether each improvement iteration continued the same chat.

Any part of this would help, in whatever form is easiest for you. I will credit your contribution and cite the data as you prefer.

Thank you for your time and for making your materials public.

Kind regards,
Marwa Chnib
PhD student, [university]
[email]
