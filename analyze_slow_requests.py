#!/usr/bin/env python3
"""
Utility per analizzare le richieste HTTP lente e i colli di bottiglia nel database.

Questo script può essere utilizzato per esplorare i log e le metriche
per identificare le cause di richieste HTTP lente.
"""

import argparse
import re
import sys
import json
from collections import defaultdict
from datetime import datetime


class StatsDMetricsAnalyzer:
    """Analizzatore di metriche StatsD per identificare problemi di performance."""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = {}
        self.gauges = {}
        self.histograms = defaultdict(list)
        self.timing_distribution = defaultdict(list)
        self.slow_requests = []
        self.database_operations = []
        self.algorithm_operations = []

    def parse_metrics_from_file(self, file_path):
        """
        Parse delle metriche da un file di log StatsD.
        
        Args:
            file_path: Percorso del file di log
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                self._parse_metrics(content)
            print(f"File analizzato con successo: {file_path}")
        except Exception as e:
            print(f"Errore durante la lettura del file: {str(e)}")
            sys.exit(1)

    def parse_metrics_from_text(self, text):
        """
        Parse delle metriche da testo.
        
        Args:
            text: Testo contenente le metriche StatsD
        """
        self._parse_metrics(text)
        print("Metriche analizzate con successo.")

    def _parse_metrics(self, content):
        """
        Analizza il contenuto delle metriche StatsD.
        
        Args:
            content: Contenuto del log StatsD
        """
        # Separa il contenuto in sezioni basate sul flush delle metriche
        sections = re.split(r'---\s+Metrics flush at.*?---', content)
        
        for section in sections:
            # Cerca le metriche principali
            metrics_match = re.findall(r'(\w+\.\w+(?:\.\w+)*)\s*=\s*([\d\.]+)', section)
            for name, value in metrics_match:
                self.metrics[name].append(float(value))
            
            # Identifica contatori
            counter_section = re.search(r'Counters:(.*?)(?:Gauges:|Histograms:|$)', section, re.DOTALL)
            if counter_section:
                counter_matches = re.findall(r'(\w+\.\w+(?:\.\w+)*)\s*=\s*([\d\.]+)', counter_section.group(1))
                for name, value in counter_matches:
                    self.counters[name] = float(value)
            
            # Identifica gauge
            gauge_section = re.search(r'Gauges:(.*?)(?:Counters:|Histograms:|$)', section, re.DOTALL)
            if gauge_section:
                gauge_matches = re.findall(r'(\w+\.\w+(?:\.\w+)*)\s*=\s*([\d\.]+)', gauge_section.group(1))
                for name, value in gauge_matches:
                    self.gauges[name] = float(value)
            
            # Identifica istogrammi
            histogram_section = re.search(r'Histograms:(.*?)(?:Counters:|Gauges:|$)', section, re.DOTALL)
            if histogram_section:
                histogram_matches = re.findall(r'(\w+\.\w+(?:\.\w+)*)\s+\(count=(\d+), min=([\d\.]+), avg=([\d\.]+), max=([\d\.]+)\)', 
                                           histogram_section.group(1))
                for name, count, min_val, avg, max_val in histogram_matches:
                    self.histograms[name] = {
                        'count': int(count),
                        'min': float(min_val),
                        'avg': float(avg),
                        'max': float(max_val)
                    }
        
        # Identifica richieste lente
        for name, values in self.metrics.items():
            if name.endswith('http.requests.slow'):
                self.slow_requests.append({
                    'name': name,
                    'count': sum(values)
                })
            
            # Raccoglie operazioni di database
            if 'db.query' in name:
                if name.endswith('.duration'):
                    self.database_operations.append({
                        'name': name,
                        'value': values[-1] if values else 0
                    })
            
            # Raccoglie operazioni di algoritmo
            if 'algorithm' in name:
                self.algorithm_operations.append({
                    'name': name,
                    'value': values[-1] if values else 0
                })

    def analyze_slow_requests(self):
        """
        Analizza le richieste HTTP lente.
        
        Returns:
            Dict con l'analisi dei problemi di performance
        """
        results = {
            'slow_requests': self.slow_requests,
            'database_operations': sorted(self.database_operations, key=lambda x: x.get('value', 0), reverse=True),
            'algorithm_operations': sorted(self.algorithm_operations, key=lambda x: x.get('value', 0), reverse=True),
            'timing_stats': {},
            'bottlenecks': [],
            'recommendations': []
        }
        
        # Analizza i colli di bottiglia basati sui timing
        if self.gauges.get('http.response.size', 0) > 10000:
            results['bottlenecks'].append({
                'type': 'response_size',
                'value': self.gauges.get('http.response.size', 0),
                'description': 'La dimensione della risposta è molto grande, potrebbe rallentare la trasmissione.'
            })
            results['recommendations'].append(
                'Considerare la paginazione o la riduzione delle dimensioni delle risposte.'
            )
        
        # Cerca operazioni database lente
        slow_db_ops = [op for op in self.database_operations if op.get('value', 0) > 500]
        if slow_db_ops:
            results['bottlenecks'].append({
                'type': 'database',
                'operations': slow_db_ops,
                'description': 'Operazioni database lente rilevate.'
            })
            results['recommendations'].append(
                'Ottimizzare le query del database o aggiungere indici appropriati.'
            )
        
        # Cerca operazioni algoritmo lente
        slow_algo_ops = [op for op in self.algorithm_operations if op.get('value', 0) > 1000]
        if slow_algo_ops:
            results['bottlenecks'].append({
                'type': 'algorithm',
                'operations': slow_algo_ops,
                'description': 'Operazioni di algoritmo lente rilevate.'
            })
            results['recommendations'].append(
                'Rivedere l\'implementazione degli algoritmi per migliorare le prestazioni.'
            )
        
        # Se ci sono statistiche di distribuzione delle durate, analizzarle
        if 'matching_service.algorithm.score.mean' in self.gauges:
            results['timing_stats']['algorithm_scores'] = {
                'min': self.gauges.get('matching_service.algorithm.score.min', 0),
                'max': self.gauges.get('matching_service.algorithm.score.max', 0),
                'mean': self.gauges.get('matching_service.algorithm.score.mean', 0),
                'median': self.gauges.get('matching_service.algorithm.score.median', 0),
                'stdev': self.gauges.get('matching_service.algorithm.score.stdev', 0)
            }
            
        return results

    def print_results(self, results=None):
        """
        Stampa i risultati dell'analisi in formato leggibile.
        
        Args:
            results: Risultati dell'analisi (opzionale)
        """
        if results is None:
            results = self.analyze_slow_requests()
        
        print("\n" + "="*80)
        print("ANALISI DELLE RICHIESTE LENTE")
        print("="*80)
        
        print("\nRichieste Lente:")
        if results['slow_requests']:
            for req in results['slow_requests']:
                print(f"  {req['name']}: {req['count']} occorrenze")
        else:
            print("  Nessuna richiesta lenta rilevata.")
        
        print("\nOperazioni Database più Lente:")
        if results['database_operations']:
            for i, op in enumerate(results['database_operations'][:5]):
                print(f"  {i+1}. {op['name']}: {op['value']:.2f} ms")
        else:
            print("  Nessuna operazione database rilevata.")
        
        print("\nOperazioni di Algoritmo più Lente:")
        if results['algorithm_operations']:
            for i, op in enumerate(results['algorithm_operations'][:5]):
                if 'duration' in op['name'] or 'score' in op['name']:
                    print(f"  {i+1}. {op['name']}: {op['value']:.2f} ms")
        else:
            print("  Nessuna operazione di algoritmo rilevata.")
        
        print("\nStatistiche dei Punteggi dell'Algoritmo:")
        if 'algorithm_scores' in results['timing_stats']:
            stats = results['timing_stats']['algorithm_scores']
            print(f"  Min: {stats['min']:.2f}")
            print(f"  Max: {stats['max']:.2f}")
            print(f"  Media: {stats['mean']:.2f}")
            print(f"  Mediana: {stats['median']:.2f}")
            print(f"  Deviazione standard: {stats['stdev']:.2f}")
        else:
            print("  Nessuna statistica disponibile.")
        
        print("\nColli di Bottiglia Identificati:")
        if results['bottlenecks']:
            for i, bottleneck in enumerate(results['bottlenecks']):
                print(f"  {i+1}. {bottleneck['description']}")
                if bottleneck['type'] == 'response_size':
                    print(f"     Dimensione risposta: {bottleneck['value']} bytes")
                elif 'operations' in bottleneck:
                    for op in bottleneck['operations'][:3]:
                        print(f"     - {op['name']}: {op['value']:.2f} ms")
        else:
            print("  Nessun collo di bottiglia identificato.")
        
        print("\nRaccomandazioni:")
        if results['recommendations']:
            for i, rec in enumerate(results['recommendations']):
                print(f"  {i+1}. {rec}")
        else:
            print("  Nessuna raccomandazione disponibile.")
        
        print("\nDiagnosi Finale:")
        if results['bottlenecks']:
            if any(b['type'] == 'database' for b in results['bottlenecks']):
                print("  Le query del database sembrano essere la causa principale dei tempi di risposta lenti.")
            elif any(b['type'] == 'algorithm' for b in results['bottlenecks']):
                print("  Gli algoritmi di matching sembrano essere la causa principale dei tempi di risposta lenti.")
            elif any(b['type'] == 'response_size' for b in results['bottlenecks']):
                print("  La dimensione delle risposte sembra essere la causa principale dei tempi di risposta lenti.")
            else:
                print("  Sono stati rilevati diversi possibili colli di bottiglia.")
        else:
            print("  Non sono stati rilevati problemi significativi nelle metriche analizzate.")
        
        print("\n" + "="*80)

    def export_results(self, output_file, results=None):
        """
        Esporta i risultati in un file JSON.
        
        Args:
            output_file: Percorso del file di output
            results: Risultati da esportare (opzionale)
        """
        if results is None:
            results = self.analyze_slow_requests()
        
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Risultati esportati in: {output_file}")
        except Exception as e:
            print(f"Errore durante l'esportazione dei risultati: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Analizzatore di metriche StatsD per problemi di performance')
    parser.add_argument('--file', '-f', help='File di log StatsD da analizzare')
    parser.add_argument('--output', '-o', help='File di output per i risultati JSON')
    parser.add_argument('--stdin', '-s', action='store_true', help='Leggi le metriche da stdin')
    
    args = parser.parse_args()
    
    analyzer = StatsDMetricsAnalyzer()
    
    if args.stdin:
        print("Inserisci le metriche StatsD (premi Ctrl+D per terminare):")
        content = sys.stdin.read()
        analyzer.parse_metrics_from_text(content)
    elif args.file:
        analyzer.parse_metrics_from_file(args.file)
    else:
        parser.print_help()
        sys.exit(1)
    
    results = analyzer.analyze_slow_requests()
    analyzer.print_results(results)
    
    if args.output:
        analyzer.export_results(args.output, results)


if __name__ == '__main__':
    main()