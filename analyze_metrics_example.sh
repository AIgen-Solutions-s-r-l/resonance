#!/bin/bash
# Esempio di utilizzo dello script analyze_slow_requests.py

# Salva le metriche in un file
cat << 'EOF' > sample_metrics.txt
matching_service.algorithm.path = 1.00
matching_service.algorithm.match_count = 5.00
matching_service.algorithm.score.min = 0.93
matching_service.algorithm.score.max = 1.00
matching_service.algorithm.score.mean = 0.95
matching_service.algorithm.score.median = 0.94
matching_service.algorithm.score.stdev = 0.03
matching_service.algorithm.score.distribution = 1.00
matching_service.algorithm.score.distribution = 0.95
matching_service.algorithm.score.distribution = 0.94
matching_service.algorithm.score.distribution = 0.94
matching_service.algorithm.score.distribution = 0.93
matching_service.algorithm.result_size = 5.00
matching_service.algorithm.result_size = 1.00
matching_service.http.requests.slow = 1.00
matching_service.http.response.size = 11823.00

--- Metrics flush at 2025-03-07T22:01:54.269299 ---

Counters:
  matching_service.algorithm.path = 1.00
  matching_service.http.requests.slow = 1.00

Gauges:
  matching_service.algorithm.match_count = 5.00
  matching_service.algorithm.result_size = 1.00
  matching_service.algorithm.score.max = 1.00
  matching_service.algorithm.score.mean = 0.95
  matching_service.algorithm.score.median = 0.94
  matching_service.algorithm.score.min = 0.93
  matching_service.algorithm.score.stdev = 0.03
  matching_service.http.response.size = 11823.00

Histograms:
  matching_service.algorithm.score.distribution (count=5, min=0.93, avg=0.95, max=1.00) {}

--- End metrics (16 received) ---
EOF

# Rendi lo script di analisi eseguibile
chmod +x analyze_slow_requests.py

# Esegui l'analisi
echo -e "\nAnalisi delle metriche di esempio:\n"
./analyze_slow_requests.py --file sample_metrics.txt

# Esporta i risultati in JSON (opzionale)
echo -e "\nEsportazione dei risultati in JSON:\n"
./analyze_slow_requests.py --file sample_metrics.txt --output metrics_analysis.json

echo -e "\nPer analizzare altre metriche, puoi usare:"
echo "  - Pipe: cat other_metrics.txt | ./analyze_slow_requests.py --stdin"
echo "  - File: ./analyze_slow_requests.py --file other_metrics.txt"
echo "  - Input manuale: ./analyze_slow_requests.py --stdin (poi incolla le metriche)"