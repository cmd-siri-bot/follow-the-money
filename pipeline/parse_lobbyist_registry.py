"""Flatten the Lobbyist Registry XML (data/raw/lobbyist_registry/lobbyactivity.zip) into
normalized CSVs under data/interim/. Streams via iterparse since the closed-activity
file is ~150MB uncompressed.

Produces:
  - lobbyist_subject_matters.csv : one row per SM registration (incl. registrant details)
  - lobbyist_communications.csv  : one row per communication event, FK subject_matter_number
  - lobbyist_beneficiaries.csv   : one row per beneficiary (client/parent), FK subject_matter_number
  - lobbyist_firms.csv           : one row per firm (consultant), FK subject_matter_number
"""
import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

RAW_ZIP = Path(__file__).resolve().parent.parent / "data" / "raw" / "lobbyist_registry" / "lobbyactivity.zip"
INTERIM_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"

SM_MEMBERS = [
    "SMNumber", "Status", "Type", "SubjectMatter", "Particulars",
    "SubjectMatterDefinition", "InitialApprovalDate", "EffectiveDate",
    "ProposedStartDate", "ProposedEndDate",
]

REGISTRANT_MEMBERS = [
    "RegistrationNUmber", "RegistrationNUmberWithSoNum", "Status", "EffectiveDate",
    "Type", "Prefix", "FirstName", "MiddleInitials", "LastName", "Suffix",
    "PositionTitle", "PreviousPublicOfficeHolder", "PreviousPublicOfficeHoldPosition",
    "PreviousPublicOfficePositionProgramName", "PreviousPublicOfficeHoldLastDate",
]

ADDRESS_MEMBERS = ["AddressLine1", "AddressLine2", "City", "Province", "Country", "PostalCode", "Phone"]

COMMUNICATION_MEMBERS = [
    "POH_Office", "POH_Type", "POH_Position", "POH_Name", "CommunicationMethod",
    "CommunicationDate", "CommunicationGroupId", "LobbyistNumber", "LobbyistType",
    "LobbyistPrefix", "LobbyistFirstName", "LobbyistMiddleInitials", "LobbyistLastName",
]

BENEFICIARY_MEMBERS = ["Type", "Name", "TradeName", "FiscalStart", "FiscalEnd"]
FIRM_MEMBERS = ["Type", "Name", "TradeName", "FiscalStart", "FiscalEnd", "Description", "BusinessType"]


def text(elem, tag):
    child = elem.find(tag)
    return child.text.strip() if child is not None and child.text else ""


def flatten_address(elem, prefix):
    addr = elem.find("BusinessAddress")
    out = {}
    if addr is not None:
        for m in ADDRESS_MEMBERS:
            out[f"{prefix}_{m}"] = text(addr, m)
    else:
        for m in ADDRESS_MEMBERS:
            out[f"{prefix}_{m}"] = ""
    return out


def parse_sm(sm_elem, source_file):
    sm_number = text(sm_elem, "SMNumber")
    row = {"source_file": source_file}
    for m in SM_MEMBERS:
        row[m] = text(sm_elem, m)

    registrant = sm_elem.find("Registrant")
    if registrant is not None:
        for m in REGISTRANT_MEMBERS:
            row[f"registrant_{m}"] = text(registrant, m)
        row.update(flatten_address(registrant, "registrant"))

    communications = []
    comms_elem = sm_elem.find("Communications")
    if comms_elem is not None:
        for comm in comms_elem.findall("Communication"):
            crow = {"subject_matter_number": sm_number, "source_file": source_file}
            for m in COMMUNICATION_MEMBERS:
                crow[m] = text(comm, m)
            communications.append(crow)

    beneficiaries = []
    ben_elem = sm_elem.find("Beneficiaries")
    if ben_elem is not None:
        for ben in ben_elem.findall("BENEFICIARY"):
            brow = {"subject_matter_number": sm_number, "source_file": source_file}
            for m in BENEFICIARY_MEMBERS:
                brow[m] = text(ben, m)
            brow.update(flatten_address(ben, "beneficiary"))
            beneficiaries.append(brow)

    firms = []
    firms_elem = sm_elem.find("Firms")
    if firms_elem is not None:
        for firm in firms_elem.findall("Firm"):
            frow = {"subject_matter_number": sm_number, "source_file": source_file}
            for m in FIRM_MEMBERS:
                frow[m] = text(firm, m)
            frow.update(flatten_address(firm, "firm"))
            firms.append(frow)

    return row, communications, beneficiaries, firms


def stream_sms(fileobj, source_file):
    for event, elem in ET.iterparse(fileobj, events=("end",)):
        if elem.tag == "SM":
            yield parse_sm(elem, source_file)
            elem.clear()


class CsvSink:
    def __init__(self, path):
        self.path = path
        self.writer = None
        self.file = None
        self.fieldnames = None

    def write(self, row):
        if self.writer is None:
            self.fieldnames = list(row.keys())
            self.file = open(self.path, "w", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)
            self.writer.writeheader()
        # tolerate rows with extra/missing keys across the two source files
        safe_row = {k: row.get(k, "") for k in self.fieldnames}
        self.writer.writerow(safe_row)

    def close(self):
        if self.file:
            self.file.close()


def main():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    sinks = {
        "sm": CsvSink(INTERIM_DIR / "lobbyist_subject_matters.csv"),
        "comm": CsvSink(INTERIM_DIR / "lobbyist_communications.csv"),
        "ben": CsvSink(INTERIM_DIR / "lobbyist_beneficiaries.csv"),
        "firm": CsvSink(INTERIM_DIR / "lobbyist_firms.csv"),
    }

    counts = {"sm": 0, "comm": 0, "ben": 0, "firm": 0}
    with zipfile.ZipFile(RAW_ZIP) as z:
        for xml_name in ["lobbyactivity-active.xml", "lobbyactivity-closed.xml"]:
            print(f"Parsing {xml_name}...")
            with z.open(xml_name) as f:
                for sm_row, comms, bens, firms in stream_sms(f, xml_name):
                    sinks["sm"].write(sm_row)
                    counts["sm"] += 1
                    for c in comms:
                        sinks["comm"].write(c)
                        counts["comm"] += 1
                    for b in bens:
                        sinks["ben"].write(b)
                        counts["ben"] += 1
                    for fr in firms:
                        sinks["firm"].write(fr)
                        counts["firm"] += 1
            print(f"  running totals: {counts}")

    for sink in sinks.values():
        sink.close()

    print("Done.", counts)


if __name__ == "__main__":
    main()
