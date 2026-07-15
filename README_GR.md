<div align="center">

# RescueMind Prototype

## Πολυπρακτορική Αντίληψη με Επίγνωση Αβεβαιότητας και Ανθρωποκεντρική Υποστήριξη Αποφάσεων Διάσωσης

**English:** [README.md](README.md) · **Ελληνικά**

</div>

<p align="center">
  <img src="assets/readme/rescuemind_pipeline.svg" alt="Εννοιολογική αρχιτεκτονική RescueMind" width="100%" />
</p>

<p align="center"><em>Εννοιολογικό διάγραμμα της ερευνητικής ροής. Δεν αποτελεί επιτόπια επικύρωση, ιατρική σύσταση, εγγύηση ασφάλειας ή αυτόνομη αρχή διάσωσης.</em></p>

## Περίληψη

Το **RescueMind-Prototype** είναι ένα ερευνητικό πρωτότυπο για τη μελέτη πολυπρακτορικής αντίληψης και υποστήριξης αποφάσεων σε συνθετικά μετακαταστροφικά περιβάλλοντα. Συνδυάζει UAV, UGV και στατικούς αισθητήρες, πολυτροπικές παρατηρήσεις, αξιολόγηση αξιοπιστίας, χρονική ευθυγράμμιση, fusion, δυναμικό ψηφιακό δίδυμο καταστροφής, υποθέσεις επιζώντων, εκτίμηση προτεραιότητας διάσωσης, ανάθεση εργασιών και ερμηνεύσιμες εξηγήσεις.

Το σύστημα δεν αποφασίζει ποιος «πρέπει» να διασωθεί αυτόνομα. Παράγει ελέγξιμα σήματα υποστήριξης αποφάσεων, μαζί με provenance, αβεβαιότητα και αιτιολόγηση, ώστε ο ανθρώπινος χειριστής να μπορεί να επιβεβαιώσει, να απορρίψει ή να παρακάμψει την πρόταση.

## Ερευνητικό ερώτημα

> Πώς μπορούν ετερογενείς και υποβαθμισμένες παρατηρήσεις από πολλαπλούς πράκτορες να συγχωνευθούν σε διαφανείς, αβέβαιες και ανθρωποκεντρικές εκτιμήσεις προτεραιότητας διάσωσης;

## Αρχιτεκτονική

```text
συνθετικό περιβάλλον καταστροφής
  → UAV / UGV / στατικοί κόμβοι
  → θερμικές, RGB, ακουστικές, radar και περιβαλλοντικές παρατηρήσεις
  → αξιοπιστία, χρονική ευθυγράμμιση και απόρριψη παλαιών δεδομένων
  → fixed / reliability-weighted / Bayesian fusion
  → ανίχνευση σύγκρουσης μεταξύ modalities
  → υποθέσεις επιζώντων και Living Disaster Twin
  → Rescue Priority Index με διαστήματα
  → communication-aware ανάθεση εργασιών
  → grounded explanation και ανθρώπινη εποπτεία
```

## Υλοποιημένο πεδίο

| Στοιχείο | Κατάσταση |
|---|---|
| Ντετερμινιστική 2-D προσομοίωση καταστροφής | Research Prototype |
| UAV, UGV και στατικός αισθητήρας | Υλοποιημένο |
| Πολυτροπικές συνθετικές παρατηρήσεις | Synthetic Validation |
| Reliability states και environment-dependent degradation | Υλοποιημένο |
| Temporal buffering και stale-data rejection | Υλοποιημένο |
| Fixed, reliability-weighted και Bayesian fusion | Υλοποιημένο |
| Provenance, duplicate rejection και conflict detection | Υλοποιημένο |
| Living Disaster Twin και hazard evolution | Research Prototype |
| Rescue Priority Index με uncertainty intervals | Υλοποιημένο |
| Communication-aware task allocation | Υλοποιημένο |
| Grounded explanations και counterfactuals | Research Prototype |
| ROS 2, εξωτερικά datasets και hardware | Εκκρεμεί επικύρωση |

## Αναπαραγωγή

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python scripts/run_all.py --mode smoke
python scripts/run_benchmark_suite.py --num-seeds 5
```

Διαθέσιμα modes: `smoke`, `perception`, `fusion`, `digital-twin`, `coordination`, `priority`, `benchmark`, `full`.

## Αξιολόγηση

Η πλατφόρμα υποστηρίζει calibration και classification metrics όπως Brier score, ECE, MCE, precision, recall και F1, καθώς και μετρικές priority reversal, communication degradation και allocation behavior. Όλες οι αριθμητικές τιμές είναι **συνθετικά ερευνητικά αποτελέσματα** και δεν αποτελούν απόδοση πραγματικής επιχείρησης διάσωσης.

## Περιορισμοί

- Δεν υπάρχει επιτόπια, hardware ή ROS 2 επικύρωση.
- Οι αισθητήρες και οι καταστροφές είναι συνθετικές προσεγγίσεις.
- Το Rescue Priority Index δεν αποτελεί ιατρικό triage ή δεοντολογική απόφαση.
- Το ψηφιακό δίδυμο και οι υποθέσεις επιζώντων είναι ερευνητικά μοντέλα.
- Το σύστημα δεν πρέπει να χρησιμοποιείται σε πραγματικές επιχειρήσεις έκτακτης ανάγκης.

## Υπεύθυνη χρήση

Το RescueMind είναι αποκλειστικά πλατφόρμα έρευνας και υποστήριξης αποφάσεων. Η τελική ευθύνη παραμένει σε κατάλληλα εκπαιδευμένους ανθρώπινους χειριστές και αρμόδιες υπηρεσίες.
