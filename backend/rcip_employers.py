"""Verified Canada RCIP Designated Employer Directory & CV Matching Engine."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from backend.rcip_data import COMMON_NOC_CATALOG, PARTICIPATING_COMMUNITIES
from backend.resume_parser import parse_resume_text

JOB_BANK_SEARCH_BASE = "https://www.jobbank.gc.ca/jobsearch/jobsearch"

OFFICIAL_EMPLOYER_TO_PR_WORKFLOW: List[Dict[str, str]] = [
    {
        "step": "1",
        "title": "Apply to Open Vacancies at Designated Employers",
        "detail": (
            "Match your CV to employers officially designated by a participating RCIP community and apply "
            "directly on their official careers portal or Canada Job Bank."
        ),
    },
    {
        "step": "2",
        "title": "Receive a Valid RCIP Job Offer (IMM 0247)",
        "detail": (
            "Confirm the offer is full-time (at least 30 paid hours/week), non-seasonal, indeterminate, inside "
            "the community's priority sectors/occupations, and at least 75% inside community boundaries."
        ),
    },
    {
        "step": "3",
        "title": "Employer Submits Your Community Recommendation -> Apply for PR",
        "detail": (
            "Once hired, the designated employer submits your Community Recommendation request to the local EDO. "
            "After the community issues your Recommendation Certificate, submit your PR application via IRCC."
        ),
    },
]

COMPLIANCE_WARNINGS: List[str] = [
    "Apply ONLY to publicly posted job vacancies — participating RCIP communities prohibit unsolicited cold-calling or mass-soliciting designated employers.",
    "Designated employer rosters and active hiring caps change monthly; verify current designation status on the community's official EDO link before accepting an offer.",
    "Under Canadian law, never pay any fee to an employer, recruiter, or third party for a job offer or community recommendation.",
]

FORBIDDEN_LOCALIZED_TERMS = ("Nigeria", "Nigerian", "Lagos", "Abuja")


DESIGNATED_EMPLOYERS_DIRECTORY: List[Dict[str, Any]] = [
    # --- Timmins, ON ---
    {
        "id": "tadh-timmins",
        "name": "Timmins & District Hospital",
        "community_id": "timmins",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32120", "31102"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "rpn", "patient care", "psw",
            "nurse aide", "medical laboratory technologist", "physician", "pharmacy",
            "healthcare", "clinical", "hospital", "emergency",
        ],
        "careers_url": "https://www.tadh.com/careers-volunteers/career-opportunities/",
        "source_portal_url": "https://timminsedc.com/immigration/",
        "location_note": "Regional referral hospital located directly inside Timmins, Ontario.",
    },
    {
        "id": "blanche-river-health-timmins",
        "name": "Blanche River Health",
        "community_id": "timmins",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32120", "44101"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "rpn", "psw", "nurse aide",
            "patient care", "lab technologist", "caregiver", "healthcare", "hospital",
        ],
        "careers_url": "https://www.blancheriverhealth.ca/about-us/current-opportunities/careers",
        "source_portal_url": "https://timminsedc.com/immigration/",
        "location_note": "Operates sites in Englehart and Kirkland Lake inside the Timmins regional RCIP catchment.",
    },
    {
        "id": "college-boreal-timmins",
        "name": "Collège Boréal",
        "community_id": "timmins",
        "sector": "Education & Childcare",
        "typical_nocs": ["42202", "21222", "22221", "11100", "10011"],
        "hiring_keywords": [
            "early childhood educator", "childcare", "college", "education", "instructor",
            "french", "bilingual", "it support", "systems analyst", "hr manager", "administration",
        ],
        "careers_url": "https://collegeboreal.wd3.myworkdayjobs.com/CB",
        "source_portal_url": "https://timminsedc.com/immigration/",
        "location_note": "Verify the posted campus/position is within Timmins or Greater Sudbury RCIP boundaries.",
    },
    {
        "id": "agnico-eagle-timmins",
        "name": "Agnico Eagle Mines Limited",
        "community_id": "timmins",
        "sector": "Mining & Natural Resources",
        "typical_nocs": ["72400", "72106", "72200", "73400", "21301", "21310"],
        "hiring_keywords": [
            "mining", "millwright", "industrial mechanic", "welder", "welding", "electrician",
            "heavy equipment", "mechanical engineer", "electrical engineer", "maintenance", "safety",
        ],
        "careers_url": "https://www.agnicoeagle.com/English/careers/default.aspx",
        "source_portal_url": "https://timminsedc.com/immigration/",
        "location_note": "Filter job openings specifically for Timmins / Detour Lake / Kirkland Lake catchment sites.",
    },
    {
        "id": "toromont-cat-timmins",
        "name": "Toromont Cat",
        "community_id": "timmins",
        "sector": "Trades & Manufacturing",
        "typical_nocs": ["72410", "72400", "72106", "73400", "73300"],
        "hiring_keywords": [
            "heavy duty mechanic", "diesel mechanic", "millwright", "welder", "welding",
            "machinist", "equipment", "caterpillar", "technician", "service", "parts",
        ],
        "careers_url": "https://www.toromontcat.com/company/careers",
        "source_portal_url": "https://timminsedc.com/immigration/",
        "location_note": "Filter job openings strictly for Timmins, Sudbury, or participating Northern Ontario branch sites.",
    },
    # --- North Bay, ON ---
    {
        "id": "ontario-northland-north-bay",
        "name": "Ontario Northland",
        "community_id": "north-bay",
        "sector": "Trades & Transport",
        "typical_nocs": ["72410", "72400", "73300", "72106", "21301", "21310", "22220"],
        "hiring_keywords": [
            "transport", "rail", "truck driver", "diesel mechanic", "heavy duty mechanic",
            "millwright", "welder", "electrician", "mechanical engineer", "network technician", "it",
        ],
        "careers_url": "https://www.ontarionorthland.ca/en/careers",
        "source_portal_url": "https://nbrcip.ca/",
        "location_note": "Verify the role is based inside the North Bay & Area (Nipissing / Parry Sound) RCIP boundary.",
    },
    # --- Sudbury, ON ---
    {
        "id": "city-greater-sudbury",
        "name": "City of Greater Sudbury",
        "community_id": "sudbury",
        "sector": "Municipal, Tech & Community Services",
        "typical_nocs": ["21231", "21232", "21222", "22220", "22221", "11100", "72200", "72300"],
        "hiring_keywords": [
            "municipal", "software engineer", "software developer", "systems analyst", "it support",
            "network technician", "cybersecurity", "sql", "javascript", "python", "accountant",
            "civil", "electrician", "plumber", "heavy equipment", "public works",
        ],
        "careers_url": "https://myjobs.greatersudbury.ca/",
        "source_portal_url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "location_note": "Public municipal employer inside Greater Sudbury RCIP & FCIP catchment.",
    },
    {
        "id": "extendicare-sudbury",
        "name": "Extendicare",
        "community_id": "sudbury",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "44101", "63200"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "rpn", "psw", "nurse aide",
            "personal support worker", "caregiver", "long term care", "cook", "dietary",
        ],
        "careers_url": "https://career.extendicare.com",
        "source_portal_url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "location_note": "Filter job listings specifically for Sudbury or Timmins RCIP locations.",
    },
    {
        "id": "paramed-sudbury",
        "name": "ParaMed Home Health Care",
        "community_id": "sudbury",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "44101"],
        "hiring_keywords": [
            "home care", "home support worker", "caregiver", "registered nurse", "nursing",
            "lpn", "rpn", "psw", "personal support worker", "patient care",
        ],
        "careers_url": "https://extendicare.wd10.myworkdayjobs.com/Paramed2023",
        "source_portal_url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "location_note": "Filter Workday requisitions to Greater Sudbury & participating RCIP community zones.",
    },
    {
        "id": "nss-canada-sudbury",
        "name": "NSS Canada",
        "community_id": "sudbury",
        "sector": "Mining & Tech",
        "typical_nocs": ["21231", "21232", "21222", "21310", "22220", "72400"],
        "hiring_keywords": [
            "software engineer", "software developer", "mining technology", "python", "typescript",
            "react", "embedded", "electronics engineer", "systems analyst", "instrumentation", "surveying",
        ],
        "careers_url": "https://www.nsscanada.com",
        "source_portal_url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "location_note": "Headquartered in Greater Sudbury serving mining automation and software systems.",
    },
    {
        "id": "orix-geo-sudbury",
        "name": "Orix Geoscience",
        "community_id": "sudbury",
        "sector": "Mining & Data/Tech",
        "typical_nocs": ["21211", "21223", "21222", "21232"],
        "hiring_keywords": [
            "data analyst", "data engineer", "data scientist", "gis", "geoscience",
            "sql", "python", "power bi", "tableau", "database", "exploration", "3d modelling",
        ],
        "careers_url": "https://www.orixgeo.com/careers",
        "source_portal_url": "https://investsudbury.ca/why-sudbury/newcomers/rcipfcip/",
        "location_note": "Confirm posted opening specifies the Sudbury office within RCIP boundaries.",
    },
    # --- Sault Ste. Marie, ON ---
    {
        "id": "tenaris-ssm",
        "name": "Tenaris (Algoma Tubes)",
        "community_id": "sault-ste-marie",
        "sector": "Manufacturing & Engineering",
        "typical_nocs": ["21301", "21310", "72400", "72100", "72106", "21222", "94140"],
        "hiring_keywords": [
            "manufacturing", "steel", "mechanical engineer", "electrical engineer", "plc",
            "millwright", "industrial mechanic", "machinist", "cnc", "welder", "quality", "maintenance",
        ],
        "careers_url": "https://www.tenaris.com/en/careers",
        "source_portal_url": "https://welcometossm.com/rcip/",
        "location_note": "Filter global careers portal strictly for Sault Ste. Marie, Ontario plant positions.",
    },
    {
        "id": "purvis-marine-ssm",
        "name": "Purvis Marine Limited",
        "community_id": "sault-ste-marie",
        "sector": "Trades & Transport",
        "typical_nocs": ["72400", "72410", "72106", "63200", "73300"],
        "hiring_keywords": [
            "marine", "mechanic", "millwright", "diesel", "welder", "cook", "galley", "transport", "logistics",
        ],
        "careers_url": "https://www.purvismarine.com",
        "source_portal_url": "https://welcometossm.com/rcip/",
        "location_note": "Confirm open postings and active RCIP hiring status on welcometossm.com/rcip/.",
    },
    # --- Thunder Bay, ON ---
    {
        "id": "lifelabs-thunder-bay",
        "name": "LifeLabs LP",
        "community_id": "thunder-bay",
        "sector": "Healthcare",
        "typical_nocs": ["32120", "31301", "32101", "33102", "21223"],
        "hiring_keywords": [
            "medical laboratory technologist", "lab technologist", "mlt", "phlebotomy",
            "registered nurse", "lpn", "patient care", "clinical", "healthcare", "data analyst",
        ],
        "careers_url": "https://www.lifelabs.com/careers/",
        "source_portal_url": "https://gotothunderbay.ca/why-thunder-bay/immigration/",
        "location_note": "Filter careers specifically to Thunder Bay / Fort William Road / Algoma Street sites.",
    },
    # --- Steinbach, MB ---
    {
        "id": "loewen-steinbach",
        "name": "Loewen Windows & Doors (C.P. Loewen Enterprises)",
        "community_id": "steinbach",
        "sector": "Manufacturing & Trades",
        "typical_nocs": ["72310", "72100", "72400", "21301", "94140", "75110"],
        "hiring_keywords": [
            "manufacturing", "carpenter", "millwork", "cnc", "machinist", "millwright",
            "industrial mechanic", "mechanical engineer", "production operator", "assembly", "lean",
        ],
        "careers_url": "https://loewencareers.com/",
        "source_portal_url": "https://steinbachedc.com/rcip/",
        "location_note": "Major designated manufacturing employer headquartered inside Steinbach, Manitoba.",
    },
    {
        "id": "hylife-steinbach",
        "name": "HyLife Ltd.",
        "community_id": "steinbach",
        "sector": "Agriculture & Food Processing",
        "typical_nocs": ["94140", "95106", "82030", "85100", "72400", "73300"],
        "hiring_keywords": [
            "food processing", "agriculture", "agri-food", "machine operator", "production operator",
            "farm supervisor", "livestock", "millwright", "maintenance mechanic", "truck driver", "qa",
        ],
        "careers_url": "https://hylife.com/career/",
        "source_portal_url": "https://steinbachedc.com/rcip/",
        "location_note": "Confirm job location is strictly within the Steinbach RCIP boundary.",
    },
    {
        "id": "big-freight-steinbach",
        "name": "Big Freight Systems",
        "community_id": "steinbach",
        "sector": "Trades & Transport",
        "typical_nocs": ["73300", "72410", "11100", "21222"],
        "hiring_keywords": [
            "truck driver", "class 1 driver", "long haul", "az driver", "commercial driver",
            "diesel mechanic", "logistics", "dispatch", "transport", "fleet",
        ],
        "careers_url": "https://www.bigfreight.com/careers",
        "source_portal_url": "https://steinbachedc.com/rcip/",
        "location_note": "Steinbach transportation & logistics employer designated on steinbachedc.com.",
    },
    {
        "id": "penn-co-steinbach",
        "name": "Penn-co Construction Canada",
        "community_id": "steinbach",
        "sector": "Trades & Construction",
        "typical_nocs": ["72310", "73400", "75110", "21301", "72200", "72300"],
        "hiring_keywords": [
            "construction", "carpenter", "framing", "heavy equipment operator", "project manager",
            "estimator", "site superintendent", "labourer", "trades",
        ],
        "careers_url": "https://www.penn-co.com/careers/",
        "source_portal_url": "https://steinbachedc.com/rcip/",
        "location_note": "Confirm posted commercial construction roles anchor at least 75% inside Steinbach RCIP boundaries.",
    },
    {
        "id": "westland-insurance-steinbach",
        "name": "Westland Insurance",
        "community_id": "steinbach",
        "sector": "Business & Finance",
        "typical_nocs": ["11100", "10011", "21222", "64100"],
        "hiring_keywords": [
            "insurance", "accountant", "finance", "business analyst", "underwriting",
            "client advisor", "sales", "administration", "customer",
        ],
        "careers_url": "https://www.westlandinsurance.ca/careers",
        "source_portal_url": "https://steinbachedc.com/rcip/",
        "location_note": "Filter careers specifically to the Steinbach, Manitoba branch location.",
    },
    # --- Brandon, MB ---
    {
        "id": "prairie-mountain-health-brandon",
        "name": "Prairie Mountain Health (Brandon Catchment)",
        "community_id": "brandon",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32102", "32120", "31102", "31120"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "nurse aide", "psw", "paramedic",
            "medical laboratory technologist", "physician", "pharmacist", "healthcare", "hospital", "clinical",
        ],
        "careers_url": "https://prairiemountainhealth.ca/careers/",
        "source_portal_url": "https://economicdevelopmentbrandon.com/rcip/rcip",
        "location_note": "IMPORTANT: Position must be physically located inside the City of Brandon RCIP boundary.",
    },
    # --- Altona / Rhineland, MB ---
    {
        "id": "friesens-altona",
        "name": "Friesens Corporation",
        "community_id": "altona-rhineland",
        "sector": "Manufacturing & Tech",
        "typical_nocs": ["72100", "72400", "21232", "21223", "94140", "11100"],
        "hiring_keywords": [
            "printing", "manufacturing", "machinist", "millwright", "production operator",
            "software developer", "data analyst", "sql", "it", "accountant", "graphic",
        ],
        "careers_url": "https://www.friesens.com/careers/",
        "source_portal_url": "https://ared-rpga.com/immigration/rcip/",
        "location_note": "Employee-owned book manufacturing hub located directly in Altona, Manitoba.",
    },
    {
        "id": "elmers-mfg-altona",
        "name": "Elmer's Manufacturing",
        "community_id": "altona-rhineland",
        "sector": "Manufacturing & Agriculture",
        "typical_nocs": ["72106", "72100", "21301", "72400", "94140", "72200"],
        "hiring_keywords": [
            "welder", "welding", "mig", "tig", "fabricator", "machinist", "cnc",
            "mechanical engineer", "solidworks", "cad", "agricultural equipment", "assembly",
        ],
        "careers_url": "https://elmersmfg.com/careers/",
        "source_portal_url": "https://ared-rpga.com/immigration/rcip/",
        "location_note": "Agricultural manufacturing employer inside the Altona / Rhineland RCIP region.",
    },
    {
        "id": "greenvalley-equipment-altona",
        "name": "Greenvalley Equipment",
        "community_id": "altona-rhineland",
        "sector": "Agriculture & Trades",
        "typical_nocs": ["72410", "72400", "82030", "73300", "64100"],
        "hiring_keywords": [
            "agricultural technician", "diesel mechanic", "heavy duty mechanic", "service technician",
            "farm", "precision ag", "parts", "john deere", "trades",
        ],
        "careers_url": "https://www.mygve.com/careers-jobs-employment-lawn-mowers-tractors-sprayers-dealership--careers",
        "source_portal_url": "https://ared-rpga.com/immigration/rcip/",
        "location_note": "Confirm job placement is specifically at the Altona dealership within ARED catchment.",
    },
    {
        "id": "access-cu-altona",
        "name": "Access Credit Union (Altona)",
        "community_id": "altona-rhineland",
        "sector": "Business & Finance",
        "typical_nocs": ["11100", "10011", "21222", "21223", "22221"],
        "hiring_keywords": [
            "finance", "banking", "credit", "accountant", "auditor", "cpa",
            "business analyst", "it support", "data analyst", "financial", "hr",
        ],
        "careers_url": "https://accesscu.wd3.myworkdayjobs.com/Access_Careers",
        "source_portal_url": "https://ared-rpga.com/immigration/rcip/",
        "location_note": "Filter Workday roles specifically to Altona / Municipality of Rhineland locations.",
    },
    # --- Moose Jaw, SK ---
    {
        "id": "city-moose-jaw",
        "name": "City of Moose Jaw",
        "community_id": "moose-jaw",
        "sector": "Municipal & Trades",
        "typical_nocs": ["73400", "72400", "72300", "72200", "21301", "21222", "11100"],
        "hiring_keywords": [
            "municipal", "public works", "heavy equipment operator", "mechanic", "plumber",
            "electrician", "engineer", "systems analyst", "accountant", "administration",
        ],
        "careers_url": "https://www.moosejaw.ca/",
        "source_portal_url": "https://rcip.mjchamber.com/",
        "location_note": "Municipal employer designated via Moose Jaw & District Chamber RCIP portal.",
    },
    {
        "id": "mnp-moose-jaw",
        "name": "MNP (Moose Jaw)",
        "community_id": "moose-jaw",
        "sector": "Business, Finance & Tech",
        "typical_nocs": ["11100", "21222", "21223", "21232", "10011"],
        "hiring_keywords": [
            "accountant", "auditor", "cpa", "tax", "advisory", "financial reporting",
            "business analyst", "cybersecurity", "data analytics", "it consultant", "erp",
        ],
        "careers_url": "https://www.mnp.ca/en/careers",
        "source_portal_url": "https://rcip.mjchamber.com/",
        "location_note": "Filter national MNP careers specifically for Moose Jaw, Saskatchewan office postings.",
    },
    # --- Pictou County, NS ---
    {
        "id": "advocate-printing-pictou",
        "name": "Advocate Printing & Publishing",
        "community_id": "pictou-county",
        "sector": "Manufacturing & Business",
        "typical_nocs": ["72100", "94140", "72400", "21232", "11100"],
        "hiring_keywords": [
            "printing", "press", "manufacturing", "machinist", "production operator",
            "maintenance", "software developer", "accountant", "graphic", "operations",
        ],
        "careers_url": "https://advocateprinting.com/careers/",
        "source_portal_url": "https://pcrcip.ca/",
        "location_note": "Filter specifically for Pictou / Stellarton / New Glasgow NS plant openings.",
    },
    # --- West Kootenay, BC ---
    {
        "id": "interior-health-west-kootenay",
        "name": "Interior Health (Trail / Nelson / Castlegar)",
        "community_id": "west-kootenay",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32120", "32102", "31120", "31102"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "nurse aide", "psw", "caregiver",
            "medical laboratory technologist", "paramedic", "pharmacist", "physician", "hospital",
        ],
        "careers_url": "https://jobs.interiorhealth.ca/",
        "source_portal_url": "https://westkootenayimmigration.ca/",
        "location_note": "Filter Interior Health job search strictly to Trail, Nelson, Castlegar, or Grand Forks.",
    },
    {
        "id": "mercer-celgar-west-kootenay",
        "name": "Mercer Celgar (Castlegar)",
        "community_id": "west-kootenay",
        "sector": "Manufacturing & Engineering",
        "typical_nocs": ["21301", "21310", "72400", "72200", "72106", "94140"],
        "hiring_keywords": [
            "pulp", "bioproducts", "mechanical engineer", "electrical engineer", "millwright",
            "industrial mechanic", "electrician", "welder", "instrumentation", "process control", "manufacturing",
        ],
        "careers_url": "https://mercerint.com/careers/",
        "source_portal_url": "https://westkootenayimmigration.ca/",
        "location_note": "Filter global careers specifically to Mercer Celgar, Castlegar, BC.",
    },
    {
        "id": "kalesnikoff-west-kootenay",
        "name": "Kalesnikoff Mass Timber",
        "community_id": "west-kootenay",
        "sector": "Manufacturing & Trades",
        "typical_nocs": ["72310", "72400", "72100", "21301", "94140", "73400"],
        "hiring_keywords": [
            "mass timber", "manufacturing", "carpenter", "cnc", "machinist", "millwright",
            "industrial mechanic", "mechanical engineer", "cad", "forestry", "heavy equipment",
        ],
        "careers_url": "https://kalesnikoff.com/careers/",
        "source_portal_url": "https://westkootenayimmigration.ca/",
        "location_note": "Operates South Slocan / Castlegar mass timber & lumber facilities in West Kootenay.",
    },
    {
        "id": "valid-mfg-west-kootenay",
        "name": "Valid Manufacturing",
        "community_id": "west-kootenay",
        "sector": "Engineering & Manufacturing",
        "typical_nocs": ["21310", "21301", "72106", "72100", "72200", "21231"],
        "hiring_keywords": [
            "electrical engineer", "mechanical engineer", "embedded", "plc", "software engineer",
            "welder", "fabricator", "cnc", "machinist", "manufacturing", "power distribution", "automation",
        ],
        "careers_url": "https://validmfg.com/careers/",
        "source_portal_url": "https://westkootenayimmigration.ca/",
        "location_note": "Check specific plant location belongs to the designating West Kootenay / Salmon Arm region.",
    },
    # --- North Okanagan-Shuswap, BC ---
    {
        "id": "interior-health-north-okanagan",
        "name": "Interior Health (Vernon / Salmon Arm)",
        "community_id": "north-okanagan-shuswap",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32120", "32102", "31120", "31102"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "nurse aide", "psw", "medical laboratory technologist",
            "paramedic", "pharmacist", "physician", "vernon jubilee", "healthcare", "hospital",
        ],
        "careers_url": "https://jobs.interiorhealth.ca/",
        "source_portal_url": "https://rcipnorthokanaganshuswap.com/",
        "location_note": "Filter Interior Health job postings strictly to Vernon, Armstrong, Enderby, or Salmon Arm.",
    },
    # --- Peace Liard, BC ---
    {
        "id": "northern-health-peace-liard",
        "name": "Northern Health Authority (Fort St. John / Dawson Creek)",
        "community_id": "peace-liard",
        "sector": "Healthcare",
        "typical_nocs": ["31301", "32101", "33102", "32120", "32102", "31120", "31102"],
        "hiring_keywords": [
            "registered nurse", "nursing", "lpn", "nurse aide", "psw", "medical laboratory technologist",
            "paramedic", "pharmacist", "physician", "hospital", "healthcare", "clinical",
        ],
        "careers_url": "https://expectmore.northernhealth.ca/",
        "source_portal_url": "https://www.nebcimmigration.ca/",
        "location_note": "Filter Northern Health openings specifically for Fort St. John, Dawson Creek, or Chetwynd.",
    },
    {
        "id": "northern-lights-college-peace-liard",
        "name": "Northern Lights College",
        "community_id": "peace-liard",
        "sector": "Education & Trades",
        "typical_nocs": ["22221", "21222", "11100", "42202", "72400", "72200"],
        "hiring_keywords": [
            "college", "instructor", "trades instructor", "it support", "systems analyst",
            "accountant", "early childhood educator", "millwright", "electrician", "administration",
        ],
        "careers_url": "https://www.nlc.bc.ca/about-nlc/careers/",
        "source_portal_url": "https://www.nebcimmigration.ca/",
        "location_note": "Regional post-secondary college operating inside Peace Liard / Northeast BC.",
    },
]


_COMMUNITIES_BY_ID: Dict[str, Dict[str, Any]] = {c["id"]: c for c in PARTICIPATING_COMMUNITIES}
_NOC_BY_CODE: Dict[str, Dict[str, Any]] = {n["noc"]: n for n in COMMON_NOC_CATALOG}


def build_job_bank_url(query: str = "", location: str = "") -> str:
    """Build a direct Government of Canada Job Bank search URL sorted newest first."""
    params: Dict[str, str] = {"sort": "M"}
    if query.strip():
        params["searchstring"] = query.strip()
    if location.strip():
        params["locationstring"] = location.strip()
    return f"{JOB_BANK_SEARCH_BASE}?{urlencode(params)}"


def validate_designated_employers_directory() -> List[str]:
    """Validate structural, URL, NOC, and domain invariants on the employer directory."""
    errors: List[str] = []
    seen_ids = set()

    for idx, emp in enumerate(DESIGNATED_EMPLOYERS_DIRECTORY):
        emp_id = str(emp.get("id") or f"idx:{idx}")
        if not emp.get("id") or not re.fullmatch(r"[a-z0-9-]+", emp_id):
            errors.append(f"Invalid employer id: {emp_id!r}")
        if emp_id in seen_ids:
            errors.append(f"Duplicate employer id: {emp_id!r}")
        seen_ids.add(emp_id)

        comm_id = str(emp.get("community_id") or "")
        if comm_id not in _COMMUNITIES_BY_ID:
            errors.append(f"{emp_id}: unknown community_id {comm_id!r}")

        for url_field in ("careers_url", "source_portal_url"):
            val = str(emp.get(url_field) or "")
            if not val.startswith("https://"):
                errors.append(f"{emp_id}: {url_field} must start with https:// (got {val!r})")

        nocs = emp.get("typical_nocs") or []
        if not nocs:
            errors.append(f"{emp_id}: typical_nocs cannot be empty")
        for noc in nocs:
            if not re.fullmatch(r"\d{5}", str(noc)):
                errors.append(f"{emp_id}: invalid 5-digit NOC {noc!r}")

        if not (emp.get("hiring_keywords") or []):
            errors.append(f"{emp_id}: hiring_keywords cannot be empty")

        blob = " ".join([
            str(emp.get("name") or ""),
            str(emp.get("sector") or ""),
            str(emp.get("location_note") or ""),
        ])
        for forbidden in FORBIDDEN_LOCALIZED_TERMS:
            if forbidden in blob:
                errors.append(f"{emp_id}: localized term {forbidden!r} is forbidden")

    return errors


def _enrich_employer(emp: Dict[str, Any], job_query: str = "") -> Dict[str, Any]:
    comm = _COMMUNITIES_BY_ID[emp["community_id"]]
    jb_loc = comm.get("job_bank_location") or f"{comm['name']}, {comm['province_code']}"
    query = job_query.strip() or (emp["typical_nocs"][0] if emp.get("typical_nocs") else "")
    return {
        **emp,
        "community_name": comm["name"],
        "province": comm["province"],
        "province_code": comm["province_code"],
        "edo_name": comm["edo_name"],
        "edo_directory_url": comm.get("employer_directory_url") or comm["official_url"],
        "job_bank_url": build_job_bank_url(query=query, location=jb_loc),
        "noc_labels": [
            f"NOC {code} — {_NOC_BY_CODE[code]['title']}" if code in _NOC_BY_CODE else f"NOC {code}"
            for code in emp.get("typical_nocs", [])
        ],
    }


def _enrich_community_directory(comm: Dict[str, Any], job_query: str = "") -> Dict[str, Any]:
    jb_loc = comm.get("job_bank_location") or f"{comm['name']}, {comm['province_code']}"
    return {
        "id": comm["id"],
        "name": comm["name"],
        "province": comm["province"],
        "province_code": comm["province_code"],
        "edo_name": comm["edo_name"],
        "official_url": comm["official_url"],
        "employer_directory_url": comm.get("employer_directory_url") or comm["official_url"],
        "key_sectors": list(comm.get("key_sectors") or []),
        "job_bank_location": jb_loc,
        "job_bank_url": build_job_bank_url(query=job_query, location=jb_loc),
    }


def list_designated_employers(
    community_id: Optional[str] = None,
    province: Optional[str] = None,
    sector: Optional[str] = None,
    noc: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """Return filtered verified designated employers plus all 14 community directories."""
    cid_filter = (community_id or "").strip().lower()
    prov_filter = (province or "").strip().lower()
    sector_filter = (sector or "").strip().lower()
    noc_filter = (noc or "").strip()
    q_filter = (q or "").strip().lower()

    results: List[Dict[str, Any]] = []
    for raw_emp in DESIGNATED_EMPLOYERS_DIRECTORY:
        enriched = _enrich_employer(raw_emp, job_query=noc_filter or q_filter)
        if cid_filter and enriched["community_id"].lower() != cid_filter:
            continue
        if prov_filter and prov_filter not in {
            enriched["province"].lower(),
            enriched["province_code"].lower(),
        }:
            continue
        if sector_filter and sector_filter not in enriched["sector"].lower():
            continue
        if noc_filter and noc_filter not in enriched["typical_nocs"]:
            continue
        if q_filter:
            haystack = " ".join([
                enriched["name"],
                enriched["community_name"],
                enriched["province"],
                enriched["sector"],
                enriched["location_note"],
                *enriched["typical_nocs"],
                *enriched["noc_labels"],
                *enriched["hiring_keywords"],
            ]).lower()
            if q_filter not in haystack:
                continue
        results.append(enriched)

    communities = [_enrich_community_directory(c, job_query=noc_filter or q_filter) for c in PARTICIPATING_COMMUNITIES]
    return {
        "total_employers": len(results),
        "employers": results,
        "communities_count": len(communities),
        "communities": communities,
        "official_workflow": OFFICIAL_EMPLOYER_TO_PR_WORKFLOW,
        "compliance_warnings": COMPLIANCE_WARNINGS,
    }


def _collect_cv_signals(
    parsed_resume: Optional[Dict[str, Any]],
    target_noc: str,
    target_title: str,
    skills: Optional[List[str]],
    suggested_nocs: Optional[List[Dict[str, Any]]],
    free_text: str,
) -> Dict[str, Any]:
    """Merge CV parser output with explicit target role/NOC/skills without inventing data."""
    parsed = dict(parsed_resume or {})
    if free_text.strip() and not parsed.get("suggested_nocs") and not parsed.get("detected_skills"):
        parsed = parse_resume_text(free_text)

    combined_skills: List[str] = []
    seen_sk = set()
    for sk in [*(parsed.get("detected_skills") or []), *(skills or [])]:
        clean = str(sk or "").strip()
        if clean and clean.lower() not in seen_sk:
            seen_sk.add(clean.lower())
            combined_skills.append(clean)

    # Ordered list of candidate NOC entries: explicit target_noc first if valid
    noc_entries: List[Dict[str, Any]] = []
    seen_nocs = set()

    clean_target_noc = re.sub(r"\D", "", str(target_noc or ""))[:5]
    if len(clean_target_noc) == 5:
        seen_nocs.add(clean_target_noc)
        catalog_hit = _NOC_BY_CODE.get(clean_target_noc)
        noc_entries.append({
            "noc": clean_target_noc,
            "title": (target_title or "").strip() or (catalog_hit["title"] if catalog_hit else f"NOC {clean_target_noc}"),
            "teer": catalog_hit["teer"] if catalog_hit else None,
            "sector": catalog_hit["sector"] if catalog_hit else "",
            "is_primary": True,
        })

    for item in [*(suggested_nocs or []), *(parsed.get("suggested_nocs") or [])]:
        code = str(item.get("noc") or "").strip()
        if not code or code in seen_nocs:
            continue
        seen_nocs.add(code)
        catalog_hit = _NOC_BY_CODE.get(code, {})
        noc_entries.append({
            "noc": code,
            "title": str(item.get("title") or catalog_hit.get("title") or code),
            "teer": item.get("teer", catalog_hit.get("teer")),
            "sector": str(item.get("sector") or catalog_hit.get("sector") or ""),
            "is_primary": len(noc_entries) == 0,
        })

    # If user typed a title/query without a known NOC, try resolving against COMMON_NOC_CATALOG
    clean_title = (target_title or "").strip()
    if clean_title and not noc_entries:
        title_lower = clean_title.lower()
        for entry in COMMON_NOC_CATALOG:
            if (
                title_lower in entry["title"].lower()
                or entry["title"].lower() in title_lower
                or any(kw in title_lower or title_lower in kw for kw in entry["keywords"])
            ):
                if entry["noc"] not in seen_nocs:
                    seen_nocs.add(entry["noc"])
                    noc_entries.append({
                        "noc": entry["noc"],
                        "title": entry["title"],
                        "teer": entry["teer"],
                        "sector": entry["sector"],
                        "is_primary": len(noc_entries) == 0,
                    })
                if len(noc_entries) >= 3:
                    break

    raw_tokens = set()
    for sk in combined_skills:
        raw_tokens.add(sk.lower())
    if clean_title:
        raw_tokens.add(clean_title.lower())
        for tok in re.findall(r"[a-z0-9+#.-]{2,}", clean_title.lower()):
            raw_tokens.add(tok)
    exp_summary = str(parsed.get("experience_summary") or free_text or "").lower()
    for tok in re.findall(r"[a-z0-9+#.-]{3,}", exp_summary[:1200]):
        raw_tokens.add(tok)

    sectors = {e["sector"] for e in noc_entries if e.get("sector")}
    return {
        "skills": combined_skills,
        "noc_entries": noc_entries,
        "sectors": sorted(sectors),
        "target_title": clean_title or (noc_entries[0]["title"] if noc_entries else ""),
        "tokens": raw_tokens,
        "has_signal": bool(combined_skills or noc_entries or clean_title or exp_summary.strip()),
    }


def _sector_tokens_match(cv_sector: str, employer_sector: str) -> bool:
    """Compare CV NOC sector labels with community/employer sector groupings."""
    a = cv_sector.lower()
    b = employer_sector.lower()
    sector_groups = (
        ("health", "caregiving", "nurse", "medical"),
        ("ict", "tech", "software", "data"),
        ("manufacturing", "engineering", "trades", "construction", "mining", "transport"),
        ("education", "childcare", "community"),
        ("business", "finance", "admin", "municipal"),
        ("agriculture", "food"),
    )
    for grp in sector_groups:
        if any(tok in a for tok in grp) and any(tok in b for tok in grp):
            return True
    return False


def match_cv_to_rcip_employers(
    parsed_resume: Optional[Dict[str, Any]] = None,
    target_noc: str = "",
    target_title: str = "",
    skills: Optional[List[str]] = None,
    suggested_nocs: Optional[List[Dict[str, Any]]] = None,
    community_id: str = "",
    province: str = "",
    sector: str = "",
    free_text: str = "",
) -> Dict[str, Any]:
    """Match a candidate's CV signals to verified RCIP designated employers with official apply URLs."""
    signals = _collect_cv_signals(
        parsed_resume=parsed_resume,
        target_noc=target_noc,
        target_title=target_title,
        skills=skills,
        suggested_nocs=suggested_nocs,
        free_text=free_text,
    )

    if not signals["has_signal"]:
        return {
            "status": "NEEDS_INPUT",
            "message": "Upload or paste your CV (or enter a target job title / 5-digit NOC) to match verified RCIP designated employers.",
            "detected_skills": [],
            "detected_nocs": [],
            "total_matched": 0,
            "matched_employers": [],
            "matched_communities": [_enrich_community_directory(c) for c in PARTICIPATING_COMMUNITIES],
            "official_workflow": OFFICIAL_EMPLOYER_TO_PR_WORKFLOW,
            "compliance_warnings": COMPLIANCE_WARNINGS,
        }

    cid_filter = (community_id or "").strip().lower()
    prov_filter = (province or "").strip().lower()
    sector_filter = (sector or "").strip().lower()

    primary_noc = signals["noc_entries"][0]["noc"] if signals["noc_entries"] else ""
    secondary_nocs = {e["noc"] for e in signals["noc_entries"][1:]}
    search_hint = signals["target_title"] or primary_noc

    matched_employers: List[Dict[str, Any]] = []
    for raw_emp in DESIGNATED_EMPLOYERS_DIRECTORY:
        comm = _COMMUNITIES_BY_ID[raw_emp["community_id"]]
        if cid_filter and raw_emp["community_id"].lower() != cid_filter:
            continue
        if prov_filter and prov_filter not in {comm["province"].lower(), comm["province_code"].lower()}:
            continue
        if sector_filter and sector_filter not in raw_emp["sector"].lower():
            continue

        score = 0
        reasons: List[str] = []
        emp_nocs = set(raw_emp.get("typical_nocs") or [])

        if primary_noc and primary_noc in emp_nocs:
            score += 50
            noc_title = _NOC_BY_CODE.get(primary_noc, {}).get("title") or primary_noc
            reasons.append(f"Directly hires for primary NOC {primary_noc} ({noc_title})")
        else:
            sec_hits = sorted(secondary_nocs & emp_nocs)
            if sec_hits:
                score += 34
                reasons.append(f"Matches detected NOC {', '.join(sec_hits)} from your CV")

        if any(_sector_tokens_match(s, raw_emp["sector"]) for s in signals["sectors"]):
            score += 22
            reasons.append(f"Operates in aligned RCIP priority sector: {raw_emp['sector']}")

        kw_hits: List[str] = []
        for kw in raw_emp.get("hiring_keywords") or []:
            kw_low = kw.lower()
            if kw_low in signals["tokens"] or any(
                len(tok) >= 4 and (tok in kw_low or kw_low in tok)
                for tok in signals["tokens"]
                if tok in {s.lower() for s in signals["skills"]} or tok in (signals["target_title"] or "").lower()
            ):
                if kw not in kw_hits:
                    kw_hits.append(kw)
        if kw_hits:
            score += min(28, len(kw_hits) * 8)
            reasons.append(f"Matched CV skills/role terms: {', '.join(kw_hits[:5])}")

        if score < 18:
            continue

        capped_score = min(100, score)
        if capped_score >= 65:
            fit_tier = "STRONG_FIT"
        elif capped_score >= 38:
            fit_tier = "GOOD_FIT"
        else:
            fit_tier = "EXPLORE_SECTOR"

        enriched = _enrich_employer(raw_emp, job_query=search_hint)
        enriched["match_score"] = capped_score
        enriched["fit_tier"] = fit_tier
        enriched["match_reasons"] = reasons
        matched_employers.append(enriched)

    matched_employers.sort(key=lambda e: (-e["match_score"], e["community_name"], e["name"]))

    # Rank all 14 communities with tailored Job Bank searches even if few named anchors exist there yet
    emp_counts_by_comm: Dict[str, int] = {}
    for e in matched_employers:
        emp_counts_by_comm[e["community_id"]] = emp_counts_by_comm.get(e["community_id"], 0) + 1

    matched_communities: List[Dict[str, Any]] = []
    for comm in PARTICIPATING_COMMUNITIES:
        sector_overlap = [
            ks for ks in comm.get("key_sectors") or []
            if any(_sector_tokens_match(cv_sec, ks) for cv_sec in signals["sectors"])
        ]
        comm_score = emp_counts_by_comm.get(comm["id"], 0) * 20 + len(sector_overlap) * 15
        entry = _enrich_community_directory(comm, job_query=search_hint)
        entry["matched_employer_count"] = emp_counts_by_comm.get(comm["id"], 0)
        entry["aligned_sectors"] = sector_overlap
        entry["priority_rank_score"] = comm_score
        matched_communities.append(entry)

    matched_communities.sort(key=lambda c: (-c["priority_rank_score"], c["name"]))

    msg = (
        f"Matched {len(matched_employers)} verified RCIP designated employer(s) across participating communities. "
        "Apply directly on each employer's official careers site or Canada Job Bank."
        if matched_employers
        else "No direct named-employer match found in our curated sample — check all 14 official community EDO portals and live Canada Job Bank links below for open postings."
    )

    return {
        "status": "MATCHED",
        "message": msg,
        "detected_skills": signals["skills"],
        "detected_nocs": signals["noc_entries"],
        "search_hint": search_hint,
        "total_matched": len(matched_employers),
        "matched_employers": matched_employers,
        "matched_communities": matched_communities,
        "official_workflow": OFFICIAL_EMPLOYER_TO_PR_WORKFLOW,
        "compliance_warnings": COMPLIANCE_WARNINGS,
    }
