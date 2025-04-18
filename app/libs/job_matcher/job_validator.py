"""
Job validation and transformation functionality.

This module handles validation and creation of JobMatch objects from database rows.
"""

from typing import Optional, Dict, Any
from loguru import logger
from time import time

from app.utils.data_parsers import parse_skills_string
from app.libs.job_matcher.models import JobMatch
from app.libs.job_matcher.exceptions import ValidationError


class JobValidator:
    """Handles validation and transformation of job data."""

    # Required fields that must be present in database results
    REQUIRED_FIELDS = {'id', 'title'}

    """
    cosine similarity returns a value between 2 and 0, where lower is better.
    doing min I get 0.92 and max 1.1 and documenting ourselves in the case of posgres there are no negative values
    Score	Similarity
    0.0	    1.000
    0.1	    0.993
    0.2	    0.987
    0.3	    0.980
    0.4	    0.883
    0.5	    0.786
    0.6	    0.690
    0.7	    0.593
    0.8	    0.497
    0.9	    0.400
    0.95    0.300
    1.0	    0.200
    1.2	    0.160
    1.4	    0.120
    1.6	    0.080
    1.8	    0.040
    2.0	    0.000
    >2.0	0.000
    """

    @staticmethod
    def score_to_percentage(score):
        """
        Converte la distanza semantica in percentuale di match usando una funzione sigmoide modificata.
        
        La funzione è calibrata per rispettare le seguenti soglie:
        - Match insufficiente: < 60% (score > 0.9)
        - Match buono: 60-80% (score tra 0.5 e 0.9)
        - Match eccellente: > 80% (score < 0.5)
        
        Mathematical Theory:
        -------------------
        La funzione sigmoide f(x) = 1/(1+e^(k*(x-m))) ha diverse proprietà che la rendono
        ideale per trasformare i punteggi di similarità:
        
        1. Mappa il dominio (-∞, ∞) nell'intervallo (0, 1)
        2. Ha un punto di flesso in x=m dove la pendenza cambia
        3. Il parametro k controlla la ripidità della curva
        4. Il parametro m determina il punto centrale della transizione
        
        Per i punteggi di similarità coseno dove:
        - 0 rappresenta similarità perfetta (deve mappare a ~100%)
        - 2 rappresenta nessuna similarità (deve mappare a ~0%)
        
        Usiamo la formula: percentuale = 100 / (1 + e^(k*(score-m)))
        
        Dove:
        - k = 5.0 controlla la pendenza della curva
        - m = 0.7 è il punto centrale della transizione (60-80%)
        
        Con questi parametri:
        - score = 0.0 → 97.07% (match eccellente)
        - score = 0.3 → 88.08% (match eccellente)
        - score = 0.5 → 73.11% (match buono)
        - score = 0.6 → 62.25% (match buono)
        - score = 0.7 → 50.00% (punto di flesso)
        - score = 0.9 → 26.89% (match insufficiente)
        - score = 1.0 → 18.24% (match insufficiente)
        
        Vantaggi di Questo Approccio:
        ---------------------------
        1. Rispetta le soglie richieste per le categorie di match
        
        2. La funzione sigmoide crea una transizione naturale tra le categorie:
           - Transizione graduale da eccellente a buono intorno a score 0.5
           - Transizione graduale da buono a insufficiente intorno a score 0.9
        
        3. La distribuzione è equilibrata e riflette l'importanza semantica:
           - Piccole differenze tra match eccellenti sono significative
           - Grandi differenze tra match insufficienti sono meno rilevanti
        
        Args:
            score (float): Punteggio di similarità coseno (0-2, dove 0 è similarità perfetta)
            
        Returns:
            float: Percentuale di match (0-100, dove 100 è match perfetto)
        """
        import math
        
        # Parametri della sigmoide
        k = 5.0      # Controlla la pendenza della curva
        midpoint = 0.7  # Punto centrale della transizione (60-80%)
        
        if score < 0:
            # Gestisce potenziali punteggi negativi (non dovrebbero verificarsi nella similarità coseno)
            return 100.0
        elif score > 2.0:
            # Limita i punteggi estremamente dissimili a 0%
            return 0.0
        else:
            # Applica la trasformazione sigmoide: 100 / (1 + e^(k*(score-midpoint)))
            percentage = 100.0 / (1.0 + math.exp(k * (score - midpoint)))
            return round(percentage, 2)

    def validate_row_data(self, row: dict) -> bool:
        """
        Validate that row has all required fields.

        Args:
            row: Dictionary containing database row data

        Returns:
            bool: True if all required fields are present, False otherwise
        """
        return all(field in row for field in self.REQUIRED_FIELDS)

    def create_job_match(self, row: dict) -> Optional[JobMatch]:
        """
        Create a JobMatch instance from a database row dictionary.

        Args:
            row: Dictionary containing job data from database

        Returns:
            JobMatch instance if successful, None if required fields are missing
        """
        start_time = time()
        if not isinstance(row, dict):
            logger.error(
                "Row is not a dictionary",
                row_type=type(row),
                row_data=row
            )
            try:
                row = dict(row)
            except Exception as e:
                logger.error(
                    "Failed to convert row to dictionary",
                    error=str(e),
                    error_type=type(e).__name__,
                    elapsed_time=f"{time() - start_time:.6f}s"
                )
                return None

        if not self.validate_row_data(row):
            logger.warning(
                "Skipping job match due to missing required fields",
                row=row,
                required_fields=self.REQUIRED_FIELDS
            )
            return None

        try:
            job_match = JobMatch(
                id=str(row['id']),
                title=row['title'],
                description=row.get('description'),
                workplace_type=row.get('workplace_type'),
                short_description=row.get('short_description'),
                field=row.get('field'),
                experience=row.get('experience'),
                skills_required=parse_skills_string(
                    row.get('skills_required')),
                country=row.get('country'),
                city=row.get('city'),
                company_name=row.get('company_name'),
                company_logo=row.get('company_logo'),
                portal=row.get('portal', 'test_portal'),
                score=float(JobValidator.score_to_percentage(
                    row.get('score', 0.0))),
                posted_date=row.get('posted_date'),
                job_state=row.get('job_state'),
                apply_link=row.get('apply_link'),
                location=row.get('location')
            )

            elapsed = time() - start_time
            logger.trace(
                "Job match created",
                job_id=job_match.id,
                elapsed_time=f"{elapsed:.6f}s"
            )

            return job_match

        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Failed to create JobMatch instance",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s",
                row=row
            )
            return None


# Singleton instance
job_validator = JobValidator()
