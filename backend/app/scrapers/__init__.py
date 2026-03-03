from dataclasses import dataclass, field

@dataclass
class ScrapedJob:
    url: str
    raw_jd: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
