"""
graph_builder.py - Knowledge graph construction module.

Parses legal documents to extract entities (cases, statutes, judges, advocates)
and creates nodes/relationships in Neo4j.
"""

import os
import re
from neo4j import GraphDatabase


class GraphBuilder:
    """Builds and queries the legal knowledge graph in Neo4j."""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "your_password",
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def create_case_node(self, case_id: str, name: str, citation: str, date: str, court: str, outcome: str = None):
        """Create a Case node."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Case {case_id: $case_id})
                SET c.name = $name,
                    c.citation = $citation,
                    c.date = $date,
                    c.court = $court,
                    c.outcome = $outcome
                """,
                case_id=case_id,
                name=name,
                citation=citation,
                date=date,
                court=court,
                outcome=outcome,
            )
    
    def create_statute_node(self, code: str, section: str, title: str, is_active: bool = True):
        """Create a Statute node."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (s:Statute {code: $code, section: $section})
                SET s.title = $title,
                    s.is_active = $is_active
                """,
                code=code,
                section=section,
                title=title,
                is_active=is_active,
            )
    
    def create_replaced_by_relationship(self, old_code: str, old_section: str, new_code: str, new_section: str, effective_date: str):
        """Create REPLACED_BY relationship between statutes."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (old:Statute {code: $old_code, section: $old_section})
                MATCH (new:Statute {code: $new_code, section: $new_section})
                MERGE (old)-[r:REPLACED_BY]->(new)
                SET r.effective_date = $effective_date
                """,
                old_code=old_code,
                old_section=old_section,
                new_code=new_code,
                new_section=new_section,
                effective_date=effective_date,
            )
    
    def create_cites_relationship(self, citing_case_id: str, cited_case_id: str):
        """Create CITES relationship between cases."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c1:Case {case_id: $citing_id})
                MATCH (c2:Case {case_id: $cited_id})
                MERGE (c1)-[:CITES]->(c2)
                """,
                citing_id=citing_case_id,
                cited_id=cited_case_id,
            )
    
    def get_bns_mapping(self, ipc_section: str) -> dict:
        """Get BNS equivalent for an IPC section."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (old:Statute {code: 'IPC', section: $section})-[r:REPLACED_BY]->(new:Statute {code: 'BNS'})
                RETURN old, new, r.effective_date as effective_date
                """,
                section=ipc_section,
            )
            record = result.single()
            if record:
                return {
                    "old": dict(record["old"]),
                    "new": dict(record["new"]),
                    "effective_date": record["effective_date"],
                }
            return None
    
    def get_citation_chain(self, case_id: str, depth: int = 3) -> list:
        """Get citation chain for a case."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (c:Case {case_id: $case_id})-[:CITES*1..$depth]->(cited:Case)
                RETURN [node in nodes(path) | {case_id: node.case_id, name: node.name}] as chain
                """,
                case_id=case_id,
                depth=depth,
            )
            chains = [record["chain"] for record in result]
            return chains


if __name__ == "__main__":
    builder = GraphBuilder()
    print("Graph builder initialized successfully.")
    builder.close()
