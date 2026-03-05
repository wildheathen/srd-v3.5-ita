#!/usr/bin/env python3
"""
Translate desc_html, traits, benefit, normal, special fields into Italian.
Covers races (traits + desc_html) and feats (benefit, normal, special).

Usage:
    python scripts/translate_descriptions.py              # all
    python scripts/translate_descriptions.py races        # only races
    python scripts/translate_descriptions.py feats        # only feats
"""

import json
import os
import sys

# ── Race translations ────────────────────────────────────────────────────

RACE_TRAITS = {
    "humans": [
        "Medio: Come creature Medie, gli umani non hanno bonus o penalità speciali dovuti alla taglia.",
        "La velocità base sul terreno degli umani è 9 metri.",
        "1 talento extra al 1° livello.",
        "4 punti abilità extra al 1° livello e 1 punto abilità extra ad ogni livello addizionale.",
        "Linguaggio automatico: Comune. Linguaggi bonus: Qualsiasi (tranne i linguaggi segreti, come il Druidico). Vedi l'abilità Parlare Linguaggi.",
        "Classe favorita: Qualsiasi. Quando si determina se un umano multiclasse subisce una penalità ai punti esperienza, la sua classe di livello più alto non conta.",
    ],
    "dwarves": [
        "+2 Costituzione, –2 Carisma.",
        "Medio: Come creature Medie, i nani non hanno bonus o penalità speciali dovuti alla taglia.",
        "La velocità base sul terreno dei nani è 6 metri. Tuttavia, i nani possono muoversi a questa velocità anche quando indossano armature medie o pesanti o quando trasportano un carico medio o pesante (a differenza delle altre creature, la cui velocità è ridotta in tali situazioni).",
        "Scurovisione: I nani possono vedere al buio fino a 18 metri. La scurovisione è solo in bianco e nero, ma per il resto è come la vista normale, e i nani possono funzionare perfettamente senza alcuna luce.",
        "Affinità con la pietra: Questa capacità garantisce a un nano un bonus razziale di +2 alle prove di Cercare per notare lavori in pietra insoliti, come pareti scorrevoli, trappole in pietra, nuove costruzioni (anche quando costruite per somigliare alle vecchie), superfici in pietra pericolose, soffitti in pietra instabili e simili. Qualcosa che non è pietra ma che è camuffato come pietra conta come lavoro in pietra insolito. Un nano che si trova semplicemente entro 3 metri da un lavoro in pietra insolito può effettuare una prova di Cercare come se stesse cercando attivamente, e un nano può usare l'abilità Cercare per trovare trappole in pietra come un ladro. Un nano può anche percepire la profondità, sentendo la sua profondità approssimativa sottoterra in modo naturale come un umano può percepire quale direzione è in alto.",
        "Familiarità con le armi: I nani possono trattare le asce da guerra naniche e gli urgrosh nanici come armi da guerra, anziché come armi esotiche.",
        "Stabilità: Un nano ottiene un bonus di +4 alle prove di caratteristica effettuate per resistere allo spingere o allo sgambetto quando si trova a terra (ma non quando scala, vola, cavalca o altrimenti non è saldamente in piedi a terra).",
        "Bonus razziale di +2 ai tiri salvezza contro il veleno.",
        "Bonus razziale di +2 ai tiri salvezza contro incantesimi ed effetti magici.",
        "Bonus razziale di +1 ai tiri per colpire contro orchi e goblinoidi.",
        "Bonus di schivare +4 alla Classe Armatura contro mostri di tipo gigante. Ogni volta che una creatura perde il suo bonus di Destrezza (se presente) alla Classe Armatura, come quando viene colta alla sprovvista, perde anche il suo bonus di schivare.",
        "Bonus razziale di +2 alle prove di Valutare relative a oggetti di pietra o metallo.",
        "Bonus razziale di +2 alle prove di Artigianato relative alla pietra o al metallo.",
        "Linguaggi automatici: Comune e Nanico. Linguaggi bonus: Gigante, Gnomesco, Goblin, Orchesco, Terran e Sottocomune.",
        "Classe favorita: Guerriero. La classe guerriero di un nano multiclasse non conta quando si determina se subisce una penalità ai punti esperienza per il multiclasse.",
    ],
    "elves": [
        "+2 Destrezza, –2 Costituzione.",
        "Medio: Come creature Medie, gli elfi non hanno bonus o penalità speciali dovuti alla taglia.",
        "La velocità base sul terreno degli elfi è 9 metri.",
        "Immunità agli effetti magici di <i>sonno</i>, e un bonus razziale di +2 ai tiri salvezza contro incantesimi o effetti di ammaliamento.",
        "Visione crepuscolare: Un elfo può vedere due volte più lontano di un umano alla luce delle stelle, della luna, delle torce e in condizioni simili di scarsa illuminazione. Conserva la capacità di distinguere colori e dettagli in queste condizioni.",
        "Competenza nelle armi: Gli elfi ricevono i talenti Competenza nelle Armi da Guerra per spada lunga, stocco, arco lungo (incluso arco lungo composito) e arco corto (incluso arco corto composito) come talenti bonus.",
        "Bonus razziale di +2 alle prove di Ascoltare, Cercare e Osservare. Un elfo che passa semplicemente entro 1,5 metri da una porta segreta o nascosta ha diritto a una prova di Cercare per notarla come se la stesse cercando attivamente.",
        "Linguaggi automatici: Comune ed Elfico. Linguaggi bonus: Draconico, Gnoll, Gnomesco, Goblin, Orchesco e Silvano.",
        "Classe favorita: Mago. La classe mago di un elfo multiclasse non conta quando si determina se subisce una penalità ai punti esperienza per il multiclasse.",
    ],
    "gnomes": [
        "+2 Costituzione, –2 Forza.",
        "Piccolo: Come creatura Piccola, uno gnomo ottiene un bonus di taglia +1 alla Classe Armatura, un bonus di taglia +1 ai tiri per colpire e un bonus di taglia +4 alle prove di Nascondersi, ma usa armi più piccole di quelle degli umani e i suoi limiti di sollevamento e trasporto sono tre quarti di quelli di un personaggio Medio.",
        "La velocità base sul terreno degli gnomi è 6 metri.",
        "Visione crepuscolare: Uno gnomo può vedere due volte più lontano di un umano alla luce delle stelle, della luna, delle torce e in condizioni simili di scarsa illuminazione. Conserva la capacità di distinguere colori e dettagli in queste condizioni.",
        "Familiarità con le armi: Gli gnomi possono trattare i martelli-uncino gnomeschi come armi da guerra anziché come armi esotiche.",
        "Bonus razziale di +2 ai tiri salvezza contro le illusioni.",
        "Aggiungere +1 alla Classe Difficoltà per tutti i tiri salvezza contro incantesimi di illusione lanciati dagli gnomi. Questo aggiustamento si cumula con quelli di effetti simili.",
        "Bonus razziale di +1 ai tiri per colpire contro coboldi e goblinoidi.",
        "Bonus di schivare +4 alla Classe Armatura contro mostri di tipo gigante. Ogni volta che una creatura perde il suo bonus di Destrezza (se presente) alla Classe Armatura, come quando viene colta alla sprovvista, perde anche il suo bonus di schivare.",
        "Bonus razziale di +2 alle prove di Ascoltare.",
        "Bonus razziale di +2 alle prove di Artigianato (alchimia).",
        "Linguaggi automatici: Comune e Gnomesco. Linguaggi bonus: Draconico, Nanico, Elfico, Gigante, Goblin e Orchesco. Inoltre, uno gnomo può parlare con un mammifero scavatore (un tasso, una volpe, un coniglio o simili, vedi sotto). Questa capacità è innata negli gnomi. Vedi la descrizione dell'incantesimo <i>parlare con gli animali</i>.",
        "Capacità magiche: 1/giorno—<i>parlare con gli animali</i> (solo mammiferi scavatori, durata 1 minuto). Uno gnomo con un punteggio di Carisma di almeno 10 ha anche le seguenti capacità magiche: 1/giorno—<i>luci danzanti, suono fantasma, prestidigitazione.</i> Livello dell'incantatore 1°; CD del tiro salvezza 10 + modificatore di Car dello gnomo + livello dell'incantesimo.",
        "Classe favorita: Bardo. La classe bardo di uno gnomo multiclasse non conta quando si determina se subisce una penalità ai punti esperienza.",
    ],
    "half-elves": [
        "Medio: Come creature Medie, i mezzelfi non hanno bonus o penalità speciali dovuti alla taglia.",
        "La velocità base sul terreno dei mezzelfi è 9 metri.",
        "Immunità agli incantesimi e agli effetti magici di <i>sonno</i>, e un bonus razziale di +2 ai tiri salvezza contro incantesimi ed effetti di ammaliamento.",
        "Visione crepuscolare: Un mezzelfo può vedere due volte più lontano di un umano alla luce delle stelle, della luna, delle torce e in condizioni simili di scarsa illuminazione. Conserva la capacità di distinguere colori e dettagli in queste condizioni.",
        "Bonus razziale di +1 alle prove di Ascoltare, Cercare e Osservare.",
        "Bonus razziale di +2 alle prove di Diplomazia e Raccogliere Informazioni.",
        "Sangue elfico: Ai fini di tutti gli effetti relativi alla razza, un mezzelfo è considerato un elfo.",
        "Linguaggi automatici: Comune ed Elfico. Linguaggi bonus: Qualsiasi (tranne i linguaggi segreti, come il Druidico).",
        "Classe favorita: Qualsiasi. Quando si determina se un mezzelfo multiclasse subisce una penalità ai punti esperienza, la sua classe di livello più alto non conta.",
    ],
    "half-orcs": [
        "+2 Forza, –2 Intelligenza, –2 Carisma.<br/>L'Intelligenza iniziale di un mezzorco è sempre almeno 3. Se questo aggiustamento la porterebbe sotto 3, è 3 invece.",
        "Medio: Come creature Medie, i mezzorchi non hanno bonus o penalità speciali dovuti alla taglia.",
        "La velocità base sul terreno dei mezzorchi è 9 metri.",
        "Scurovisione: I mezzorchi possono vedere al buio fino a 18 metri.",
        "Sangue orchesco: Ai fini di tutti gli effetti relativi alla razza, un mezzorco è considerato un orco.",
        "Linguaggi automatici: Comune e Orchesco. Linguaggi bonus: Draconico, Gigante, Gnoll, Goblin e Abissale.",
        "Classe favorita: Barbaro. La classe barbaro di un mezzorco multiclasse non conta quando si determina se subisce una penalità ai punti esperienza.",
    ],
    "halflings": [
        "+2 Destrezza, –2 Forza.",
        "Piccolo: Come creatura Piccola, un halfling ottiene un bonus di taglia +1 alla Classe Armatura, un bonus di taglia +1 ai tiri per colpire e un bonus di taglia +4 alle prove di Nascondersi, ma usa armi più piccole di quelle degli umani e i suoi limiti di sollevamento e trasporto sono tre quarti di quelli di un personaggio Medio.",
        "La velocità base sul terreno degli halfling è 6 metri.",
        "Bonus razziale di +2 alle prove di Scalare, Saltare e Muoversi Silenziosamente.",
        "Bonus razziale di +1 a tutti i tiri salvezza.",
        "Bonus razziale di +2 ai tiri salvezza contro la paura: Questo bonus si cumula con il bonus di +1 ai tiri salvezza in generale degli halfling.",
        "Bonus razziale di +1 ai tiri per colpire con armi da lancio e fionde.",
        "Bonus razziale di +2 alle prove di Ascoltare.",
        "Linguaggi automatici: Comune e Halfling. Linguaggi bonus: Nanico, Elfico, Gnomesco, Goblin e Orchesco.",
        "Classe favorita: Ladro. La classe ladro di un halfling multiclasse non conta quando si determina se subisce una penalità ai punti esperienza.",
    ],
}

# Build desc_html from traits (same format as original: <ul><li>...</li></ul>)
RACE_DESC_HTML = {}
for slug, traits in RACE_TRAITS.items():
    items = "\n".join(f"<li>{t}</li>" for t in traits)
    RACE_DESC_HTML[slug] = f"<ul>\n{items}\n</ul>"


# ── Feat prerequisites translations ──────────────────────────────────────
# Direct mapping of EN prerequisite strings to IT

FEAT_PREREQUISITES = {
    "armor-proficiency-medium": "Competenza nelle Armature (leggere).",
    "augment-summoning": "Focalizzazione Magica (evocazione).",
    "brew-potion": "Livello dell'incantatore 3°.",
    "cleave": "For 13, Attacco Poderoso.",
    "combat-expertise": "Int 13.",
    "craft-magic-arms-and-armor": "Livello dell'incantatore 5°.",
    "craft-rod": "Livello dell'incantatore 9°.",
    "craft-staff": "Livello dell'incantatore 12°.",
    "craft-wand": "Livello dell'incantatore 5°.",
    "craft-wondrous-item": "Livello dell'incantatore 3°.",
    "deflect-arrows": "Des 13, Colpo Senz'Armi Migliorato.",
    "diehard": "Resistenza Fisica.",
    "dodge": "Des 13.",
    "exotic-weapon-proficiency": "Bonus di attacco base +1 (più For 13 per spada bastarda o ascia da guerra nanica).",
    "extra-turning": "Capacità di scacciare o intimorire creature.",
    "far-shot": "Tiro Ravvicinato.",
    "feat-descriptions--armor-proficiency-heavy": "Competenza nelle Armature (leggere), Competenza nelle Armature (medie).",
    "feat-name": "Un punteggio di caratteristica minimo, un altro talento o talenti, un bonus di attacco base minimo, un numero minimo di gradi in una o più abilità, o un livello di classe che un personaggio deve avere per acquisire questo talento. Questa voce è assente se un talento non ha prerequisiti. Un talento può avere più di un prerequisito.",
    "forge-ring": "Livello dell'incantatore 12°.",
    "great-cleave": "For 13, Fendente, Attacco Poderoso, bonus di attacco base +4.",
    "greater-spell-penetration": "Penetrazione Magica.",
    "greater-two-weapon-fighting": "Des 19, Combattere con Due Armi Migliorato, Combattere con Due Armi, bonus di attacco base +11.",
    "greater-weapon-focus": "Competenza con l'arma selezionata, Focalizzazione sull'Arma con l'arma selezionata, livello da guerriero 8°.",
    "greater-weapon-specialization": "Competenza con l'arma selezionata, Focalizzazione sull'Arma Superiore con l'arma selezionata, Focalizzazione sull'Arma con l'arma selezionata, Specializzazione sull'Arma con l'arma selezionata, livello da guerriero 12°.",
    "improved-bull-rush": "For 13, Attacco Poderoso.",
    "improved-critical": "Competenza con l'arma, bonus di attacco base +8.",
    "improved-disarm": "Int 13, Competenza in Combattimento.",
    "improved-familiar": "Capacità di acquisire un nuovo famiglio, allineamento compatibile, livello sufficientemente alto (vedi sotto).",
    "improved-feint": "Int 13, Competenza in Combattimento.",
    "improved-grapple": "Des 13, Colpo Senz'Armi Migliorato.",
    "improved-overrun": "For 13, Attacco Poderoso.",
    "improved-precise-shot": "Des 19, Tiro Ravvicinato, Tiro Preciso, bonus di attacco base +11.",
    "improved-shield-bash": "Competenza negli Scudi.",
    "improved-sunder": "For 13, Attacco Poderoso.",
    "improved-trip": "Int 13, Competenza in Combattimento.",
    "improved-turning": "Capacità di scacciare o intimorire creature.",
    "improved-two-weapon-fighting": "Des 17, Combattere con Due Armi, bonus di attacco base +6.",
    "leadership": "Livello del personaggio 6°.",
    "manyshot": "Des 17, Tiro Ravvicinato, Tiro Rapido, bonus di attacco base +6.",
    "mobility": "Des 13, Schivare.",
    "mounted-archery": "Cavalcare 1 grado, Combattimento in Sella.",
    "mounted-combat": "Cavalcare 1 grado.",
    "natural-spell": "Sag 13, capacità forma selvatica.",
    "power-attack": "For 13.",
    "precise-shot": "Tiro Ravvicinato.",
    "quick-draw": "Bonus di attacco base +1.",
    "rapid-reload": "Competenza nelle Armi (tipo di balestra scelto).",
    "rapid-shot": "Des 13, Tiro Ravvicinato.",
    "ride-by-attack": "Cavalcare 1 grado, Combattimento in Sella.",
    "scribe-scroll": "Livello dell'incantatore 1°.",
    "shot-on-the-run": "Des 13, Schivare, Mobilità, Tiro Ravvicinato, bonus di attacco base +4.",
    "snatch-arrows": "Des 15, Deviare Frecce, Colpo Senz'Armi Migliorato.",
    "spell-mastery": "Livello da mago 1°.",
    "spirited-charge": "Cavalcare 1 grado, Combattimento in Sella, Attacco in Corsa.",
    "spring-attack": "Des 13, Schivare, Mobilità, bonus di attacco base +4.",
    "stunning-fist": "Des 13, Sag 13, Colpo Senz'Armi Migliorato, bonus di attacco base +8.",
    "tower-shield-proficiency": "Competenza negli Scudi.",
    "trample": "Cavalcare 1 grado, Combattimento in Sella.",
    "two-weapon-defense": "Des 15, Combattere con Due Armi.",
    "two-weapon-fighting": "Des 15.",
    "weapon-finesse": "Bonus di attacco base +1.",
    "weapon-focus": "Competenza con l'arma selezionata, bonus di attacco base +1.",
    "weapon-specialization": "Competenza con l'arma selezionata, Focalizzazione sull'Arma con l'arma selezionata, livello da guerriero 4°.",
    "whirlwind-attack": "Des 13, Int 13, Competenza in Combattimento, Schivare, Mobilità, Attacco in Movimento, bonus di attacco base +4.",
}


# ── Feat translations (benefit, normal, special) ─────────────────────────
# These are the most commonly used feats with their benefit text translated

FEAT_TRANSLATIONS = {
    "alertness": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Ascoltare e Osservare.",
        "special": "Il padrone di un famiglio ottiene il beneficio del talento Allerta ogni volta che il famiglio è entro portata di braccio.",
    },
    "blind-fight": {
        "benefit": "In mischia, ogni volta che manchi a causa dell'occultamento, puoi ritirare la percentuale di mancamento per vedere se effettivamente colpisci. Un attaccante invisibile non ottiene vantaggi ai tiri per colpire contro di te in mischia. Cioè, non perdi il tuo bonus di Destrezza alla Classe Armatura, e l'attaccante non ottiene il solito bonus di +2 per l'invisibilità. Tuttavia, l'attaccante invisibile ottiene ancora il beneficio dell'occultamento totale (50% di probabilità di mancamento). Non hai bisogno di effettuare prove di Acrobazia per muoverti alla velocità piena in oscurità totale.",
        "normal": "La mischia regolare contro un avversario con occultamento richiede una prova di mancamento. I nemici invisibili ottengono vantaggi ai tiri per colpire contro di te in mischia.",
        "special": "Il talento Combattere alla Cieca non ha effetto contro un personaggio che è oggetto di un incantesimo di <i>intermittenza</i>.",
    },
    "cleave": {
        "benefit": "Se colpisci un avversario con sufficiente danno da farlo cadere (tipicamente riducendo i suoi punti ferita sotto 0 o uccidendolo), ottieni un attacco in mischia extra immediato contro un'altra creatura nelle vicinanze. Non puoi fare un passo di 1,5 m prima di effettuare questo attacco extra. L'attacco extra è al tuo bonus di attacco completo, anche se hai già attaccato in quel round. Puoi usare questa capacità una volta per round.",
        "special": "Un guerriero può selezionare Fendente come uno dei suoi talenti bonus da guerriero.",
    },
    "combat-casting": {
        "benefit": "Ottieni un bonus di +4 alle prove di Concentrazione effettuate per lanciare un incantesimo o usare una capacità magica mentre sei sulla difensiva o mentre sei in lotta.",
    },
    "combat-expertise": {
        "benefit": "Quando usi l'azione di attacco o l'azione di attacco completo in mischia, puoi subire una penalità di –1 ai tiri per colpire in mischia e ottenere un bonus di schivare +1 alla Classe Armatura. Questa penalità e bonus aumentano di 1 per ogni –1 nei tiri per colpire, fino a un massimo di –5/+5. Devi scegliere di usare questa capacità prima di effettuare un tiro per colpire, e i suoi effetti durano fino alla tua prossima azione.",
        "normal": "Un personaggio senza il talento Competenza in Combattimento può combattere sulla difensiva mentre usa l'azione di attacco o l'azione di attacco completo per subire una penalità di –4 ai tiri per colpire e ottenere un bonus di schivare +2 alla Classe Armatura.",
        "special": "Un guerriero può selezionare Competenza in Combattimento come uno dei suoi talenti bonus da guerriero.",
    },
    "combat-reflexes": {
        "benefit": "Puoi effettuare un numero di attacchi di opportunità aggiuntivi in un round pari al tuo bonus di Destrezza. Con questo talento puoi anche effettuare attacchi di opportunità quando sei colto alla sprovvista.",
        "normal": "Un personaggio senza questo talento può effettuare solo un attacco di opportunità per round e non può effettuare attacchi di opportunità quando è colto alla sprovvista.",
        "special": "Il talento Riflessi in Combattimento non ti permette di effettuare più di un attacco di opportunità per la stessa circostanza.",
    },
    "dodge": {
        "benefit": "Durante la tua azione, designa un avversario e ricevi un bonus di schivare +1 alla Classe Armatura contro gli attacchi di quell'avversario. Puoi selezionare un nuovo avversario su ogni azione. Un bonus di schivare si cumula con tutti gli altri bonus di schivare che puoi avere.",
        "special": "Un guerriero può selezionare Schivare come uno dei suoi talenti bonus da guerriero.",
    },
    "endurance": {
        "benefit": "Ottieni un bonus di +4 alle seguenti prove e tiri salvezza: Nuotare per resistere a danni non letali da esaurimento; prove di Costituzione per continuare a correre; prove di Costituzione per evitare danni non letali da marcia forzata; prove di Costituzione per trattenere il respiro; prove di Costituzione per evitare danni da fame o sete; tiri salvezza sulla Tempra per evitare danni non letali da ambiente caldo o freddo; e tiri salvezza sulla Tempra per resistere a danni da soffocamento. Inoltre puoi dormire in armatura leggera o media senza affaticarti.",
        "normal": "Un personaggio senza questo talento che dorme in armatura media o più pesante è automaticamente affaticato il giorno successivo.",
        "special": "Un ranger ottiene automaticamente Resistenza Fisica come talento bonus al 3° livello. Non ha bisogno di selezionarlo.",
    },
    "great-cleave": {
        "benefit": "Questo talento funziona come Fendente, eccetto che non c'è limite al numero di volte che puoi usarlo per round.",
        "special": "Un guerriero può selezionare Fendente Poderoso come uno dei suoi talenti bonus da guerriero.",
    },
    "great-fortitude": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sulla Tempra.",
    },
    "improved-bull-rush": {
        "benefit": "Quando effettui uno spingere, non provochi un attacco di opportunità dal difensore. Ottieni anche un bonus di +4 alla prova di Forza per spingere.",
        "special": "Un guerriero può selezionare Spingere Migliorato come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-critical": {
        "benefit": "Quando usi l'arma selezionata, il suo intervallo di minaccia di critico è raddoppiato.",
        "special": "Puoi ottenere Critico Migliorato più volte. Gli effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma. Questo effetto non si cumula con nessun altro effetto che espande l'intervallo di minaccia di un'arma.",
    },
    "improved-disarm": {
        "benefit": "Non provochi un attacco di opportunità quando tenti di disarmare un avversario, né l'avversario ha la possibilità di disarmarti. Ottieni anche un bonus di +4 alla prova di attacco per disarmare il tuo avversario.",
        "normal": "Senza questo talento, tentare di disarmare provoca un attacco di opportunità.",
        "special": "Un guerriero può selezionare Disarmare Migliorato come uno dei suoi talenti bonus da guerriero. Un monaco può selezionare Disarmare Migliorato come talento bonus al 6° livello, anche se non ne soddisfa i prerequisiti.",
    },
    "improved-grapple": {
        "benefit": "Non provochi un attacco di opportunità quando effettui un attacco di contatto per iniziare una lotta. Ottieni anche un bonus di +4 a tutte le prove di lotta, indipendentemente dal fatto che tu abbia iniziato la lotta o meno.",
        "normal": "Senza questo talento, effettuare una lotta provoca un attacco di opportunità.",
        "special": "Un guerriero può selezionare Lotta Migliorata come uno dei suoi talenti bonus da guerriero. Un monaco può selezionare Lotta Migliorata come talento bonus al 1° livello, anche se non ne soddisfa i prerequisiti.",
    },
    "improved-initiative": {
        "benefit": "Ottieni un bonus di +4 alle prove di iniziativa.",
        "special": "Un guerriero può selezionare Iniziativa Migliorata come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-overrun": {
        "benefit": "Quando tenti di travolgere un avversario, il bersaglio non può scegliere di evitarti. Ottieni anche un bonus di +4 alla prova di Forza per abbattere il tuo avversario.",
        "normal": "Senza questo talento, il bersaglio di un travolgimento può scegliere di farsi da parte.",
        "special": "Un guerriero può selezionare Travolgere Migliorato come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-shield-bash": {
        "benefit": "Quando effettui un colpo con lo scudo, puoi comunque applicare il bonus dello scudo alla CA.",
        "normal": "Senza questo talento, un personaggio che effettua un colpo con lo scudo perde il bonus dello scudo alla CA fino alla sua prossima azione.",
        "special": "Un guerriero può selezionare Colpo con lo Scudo Migliorato come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-sunder": {
        "benefit": "Quando colpisci un oggetto tenuto o indossato con un attacco per distruggere, non provochi un attacco di opportunità. Ottieni anche un bonus di +4 alla prova di attacco per distruggere.",
        "normal": "Senza questo talento, tentare di distruggere un oggetto provoca un attacco di opportunità.",
        "special": "Un guerriero può selezionare Distruggere Migliorato come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-trip": {
        "benefit": "Non provochi un attacco di opportunità quando tenti di sgambettare un avversario mentre sei in mischia. Ottieni anche un bonus di +4 alla prova di Forza per sgambettare. Se sgambetti con successo un avversario, ottieni immediatamente un attacco in mischia contro quell'avversario come se non avessi usato il tuo attacco per lo sgambetto.",
        "normal": "Senza questo talento, tentare uno sgambetto provoca un attacco di opportunità.",
        "special": "Al 6° livello, un monaco può selezionare Sgambetto Migliorato come talento bonus, anche se non ne soddisfa i prerequisiti.",
    },
    "improved-turning": {
        "benefit": "Aggiungi un bonus di +1 al tuo livello di scacciare quando fai una prova di scacciare per determinare il Dado Vita massimo della creatura non morta che puoi influenzare.",
    },
    "improved-two-weapon-fighting": {
        "benefit": "Oltre al normale attacco extra con un'arma secondaria, ottieni un secondo attacco con essa, anche se con una penalità di –5.",
        "normal": "Senza questo talento, puoi ottenere solo un singolo attacco extra con un'arma secondaria.",
        "special": "Un guerriero può selezionare Combattere con Due Armi Migliorato come uno dei suoi talenti bonus da guerriero. Un ranger di 6° livello che ha scelto lo stile di combattimento con due armi è considerato come se avesse Combattere con Due Armi Migliorato, anche se non ne soddisfa i prerequisiti.",
    },
    "improved-unarmed-strike": {
        "benefit": "Sei considerato armato anche quando sei disarmato—cioè, non provochi attacchi di opportunità da avversari armati quando li attacchi disarmato. Tuttavia, provochi ancora attacchi di opportunità come normale se effettui un attacco disarmato quando minacciato da un avversario che non stai attaccando.",
        "normal": "Senza questo talento, sei considerato disarmato quando attacchi con un colpo senz'armi e provochi un attacco di opportunità da avversari armati.",
        "special": "Un monaco ottiene automaticamente Colpo Senz'Armi Migliorato come talento bonus al 1° livello. Non ha bisogno di selezionarlo.",
    },
    "iron-will": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sulla Volontà.",
    },
    "lightning-reflexes": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sui Riflessi.",
    },
    "mobility": {
        "benefit": "Ottieni un bonus di schivare +4 alla Classe Armatura contro attacchi di opportunità causati dal muoversi fuori da o dentro un'area minacciata. Un bonus di schivare di questo tipo non si applica se perdi il tuo bonus di Destrezza alla CA.",
        "special": "Un guerriero può selezionare Mobilità come uno dei suoi talenti bonus da guerriero.",
    },
    "mounted-archery": {
        "benefit": "La penalità che subisci quando usi un'arma a distanza mentre sei in sella è dimezzata: –2 invece di –4 se la cavalcatura compie un doppio movimento, e –4 invece di –8 se la cavalcatura corre.",
        "special": "Un guerriero può selezionare Tiro in Sella come uno dei suoi talenti bonus da guerriero.",
    },
    "mounted-combat": {
        "benefit": "Una volta per round quando la tua cavalcatura è colpita in combattimento, puoi tentare una prova di Cavalcare (come reazione) per negare il colpo. La prova di Cavalcare sostituisce la CA della cavalcatura. Se il risultato della tua prova di Cavalcare è maggiore del tiro per colpire, il colpo manca.",
        "special": "Un guerriero può selezionare Combattere in Sella come uno dei suoi talenti bonus da guerriero.",
    },
    "natural-spell": {
        "benefit": "Puoi completare le componenti verbali e somatiche degli incantesimi mentre sei in forma selvatica. Puoi anche usare qualsiasi focus materiale o focus divino che porti incorporato nella tua forma selvatica.",
    },
    "point-blank-shot": {
        "benefit": "Ottieni un bonus di +1 ai tiri per colpire e ai tiri per i danni con armi a distanza a portata fino a 9 metri.",
        "special": "Un guerriero può selezionare Tiro Ravvicinato come uno dei suoi talenti bonus da guerriero.",
    },
    "power-attack": {
        "benefit": "Nel tuo turno, prima di effettuare tiri per colpire per un round, puoi scegliere di sottrarre un numero dal tuo tiro per colpire in mischia e aggiungere lo stesso numero al tuo tiro per i danni in mischia. Questo numero non può superare il tuo bonus di attacco base. La penalità ai tiri per colpire e il bonus ai danni si applicano fino alla tua prossima azione.",
        "special": "Se attacchi con un'arma a due mani, aggiungi invece il doppio del numero sottratto dai tiri per colpire. Non puoi aggiungere il bonus ai danni con un'arma leggera.",
    },
    "precise-shot": {
        "benefit": "Puoi sparare o lanciare armi a distanza su un bersaglio impegnato in mischia senza subire la penalità standard di –4 al tiro per colpire.",
        "special": "Un guerriero può selezionare Tiro Preciso come uno dei suoi talenti bonus da guerriero.",
    },
    "quick-draw": {
        "benefit": "Puoi estrarre un'arma come azione gratuita invece che come azione di movimento. Puoi lanciare armi alla massima velocità di attacco (molto simile alla penalità per gli attacchi in mischia).",
        "normal": "Senza questo talento, puoi estrarre un'arma come azione di movimento, o (se il tuo bonus di attacco base è +1 o superiore) come azione gratuita come parte di un movimento.",
        "special": "Un guerriero può selezionare Estrazione Rapida come uno dei suoi talenti bonus da guerriero.",
    },
    "rapid-shot": {
        "benefit": "Puoi ottenere un attacco a distanza extra per round. Tutti i tuoi tiri per colpire per il round subiscono una penalità di –2 quando usi Tiro Rapido.",
        "special": "Un guerriero può selezionare Tiro Rapido come uno dei suoi talenti bonus da guerriero. Un ranger di 2° livello che ha scelto lo stile di combattimento con arco è considerato come se avesse Tiro Rapido, anche se non ne soddisfa i prerequisiti.",
    },
    "ride-by-attack": {
        "benefit": "Quando sei in sella e usi l'azione di carica, puoi muoverti e attaccare come con una carica standard e poi continuare a muoverti (fino al doppio della velocità della cavalcatura). Devi muoverti almeno di 3 metri prima e dopo l'attacco.",
        "special": "Un guerriero può selezionare Attacco in Corsa a Cavallo come uno dei suoi talenti bonus da guerriero.",
    },
    "run": {
        "benefit": "Quando corri, ti muovi a cinque volte la tua velocità normale (se indossi armatura media, leggera o nessuna e trasporti un carico non più che medio) o a quattro volte la tua velocità (se indossi armatura pesante o trasporti un carico pesante). Se effettui un salto dopo una rincorsa, ottieni un bonus di +4 alla prova di Saltare.",
        "normal": "Ti muovi a quattro volte la tua velocità mentre corri (se indossi armatura media, leggera o nessuna e trasporti un carico non più che medio) o a tre volte la tua velocità (se indossi armatura pesante o trasporti un carico pesante).",
    },
    "self-sufficient": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Guarire e Sopravvivenza.",
    },
    "shield-proficiency": {
        "benefit": "Puoi usare uno scudo e non subire la penalità all'attacco associata.",
        "normal": "Quando usi uno scudo con cui non sei competente, subisci la penalità di controllo dell'armatura dello scudo ai tiri per colpire e a tutte le prove di abilità che comportano movimento.",
        "special": "Barbari, bardi, chierici, druidi, guerrieri, paladini e ranger hanno automaticamente Competenza negli Scudi come talento bonus. Non hanno bisogno di selezionarlo.",
    },
    "spell-focus": {
        "benefit": "Aggiungi +1 alla Classe Difficoltà per tutti i tiri salvezza contro gli incantesimi della scuola di magia selezionata.",
        "special": "Puoi ottenere questo talento più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a una nuova scuola di magia.",
    },
    "spell-penetration": {
        "benefit": "Ottieni un bonus di +2 alle prove di livello dell'incantatore (1d20 + livello dell'incantatore) effettuate per superare la resistenza agli incantesimi di una creatura.",
    },
    "spirited-charge": {
        "benefit": "Quando sei in sella e usi l'azione di carica, infliggi il doppio dei danni con un'arma da mischia (o il triplo dei danni con una lancia).",
        "special": "Un guerriero può selezionare Carica Impetuosa come uno dei suoi talenti bonus da guerriero.",
    },
    "spring-attack": {
        "benefit": "Quando usi l'azione di attacco con un'arma da mischia, puoi muoverti sia prima che dopo l'attacco, purché la distanza totale che percorri non sia maggiore della tua velocità. Muoversi in questo modo non provoca un attacco di opportunità dal difensore che stai attaccando.",
        "special": "Un guerriero può selezionare Attacco in Movimento come uno dei suoi talenti bonus da guerriero.",
    },
    "stealthy": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Nascondersi e Muoversi Silenziosamente.",
    },
    "stunning-fist": {
        "benefit": "Devi dichiarare di usare questo talento prima di effettuare il tiro per colpire (quindi un attacco mancato spreca il tentativo). Pugno Stordente costringe un avversario colpito da te con un attacco senz'armi a effettuare un tiro salvezza sulla Tempra (CD 10 + metà del tuo livello del personaggio + il tuo modificatore di Sag), oltre a subire danni normali. Se il difensore fallisce il tiro salvezza, è stordito per 1 round.",
        "special": "Puoi tentare uno stordimento una volta al giorno per ogni quattro livelli che hai raggiunto, e non più di una volta per round.",
    },
    "toughness": {
        "benefit": "Ottieni +3 punti ferita.",
        "special": "Un personaggio può ottenere questo talento più volte. I suoi effetti si cumulano.",
    },
    "track": {
        "benefit": "Per trovare le tracce o per seguirle per 1,5 km richiede una prova di Sopravvivenza riuscita. Devi effettuare un'altra prova di Sopravvivenza ogni volta che le tracce diventano difficili da seguire.",
        "normal": "Senza questo talento, puoi usare l'abilità Sopravvivenza per trovare le tracce, ma puoi seguirle solo se la CD è 10 o inferiore. In alternativa, puoi usare la prova di Cercare per trovare delle impronte o segni simili.",
        "special": "Un ranger ottiene automaticamente Seguire Tracce come talento bonus. Non ha bisogno di selezionarlo. Questo talento non ti permette di trovare o seguire le tracce di soggetti con il talento Passo senza Tracce.",
    },
    "two-weapon-fighting": {
        "benefit": "Le tue penalità al combattimento con due armi sono ridotte di 2 con l'arma primaria e di 6 con l'arma secondaria.",
        "normal": "Se impugni una seconda arma nella mano secondaria, puoi ottenere un attacco extra con quell'arma al costo di una penalità di –6 ai tiri per colpire con l'arma primaria e una penalità di –10 con l'arma secondaria.",
        "special": "Un ranger di 2° livello che ha scelto lo stile di combattimento con due armi è considerato come se avesse Combattere con Due Armi, anche se non ne soddisfa i prerequisiti.",
    },
    "weapon-finesse": {
        "benefit": "Con un'arma leggera, stocco, frusta o catena chiodata fatta per una creatura della tua categoria di taglia, puoi usare il tuo modificatore di Destrezza invece del tuo modificatore di Forza ai tiri per colpire in mischia.",
        "special": "Un guerriero può selezionare Arma Accurata come uno dei suoi talenti bonus da guerriero. Le creature naturali possono selezionare questo talento.",
    },
    "weapon-focus": {
        "benefit": "Ottieni un bonus di +1 a tutti i tiri per colpire effettuati usando l'arma selezionata.",
        "special": "Puoi ottenere questo talento più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma.",
    },
    "whirlwind-attack": {
        "benefit": "Quando usi l'azione di attacco completo, puoi rinunciare ai tuoi attacchi regolari e invece effettuare un attacco in mischia al tuo bonus di attacco base completo contro ogni avversario entro la tua portata.",
        "special": "Un guerriero può selezionare Attacco Turbinante come uno dei suoi talenti bonus da guerriero.",
    },
    "acrobatic": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Saltare e Acrobazia.",
    },
    "agile": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Equilibrio e Artista della Fuga.",
    },
    "animal-affinity": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Addestrare Animali e Cavalcare.",
    },
    "armor-proficiency-medium": {
        "benefit": "Vedi Competenza nelle Armature (leggere).",
        "normal": "Vedi Competenza nelle Armature (leggere).",
        "special": "Guerrieri, barbari, paladini, chierici, druidi e bardi hanno automaticamente Competenza nelle Armature (medie) come talento bonus. Non hanno bisogno di selezionarlo.",
    },
    "athletic": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Scalare e Nuotare.",
    },
    "augment-summoning": {
        "benefit": "Ogni creatura che evochi con qualsiasi incantesimo di evocazione ottiene un bonus di potenziamento di +4 a Forza e Costituzione per la durata dell'incantesimo che l'ha evocata.",
    },
    "brew-potion": {
        "benefit": "Puoi creare una pozione di qualsiasi incantesimo di 3° livello o inferiore che conosci e che ha come bersaglio una o più creature. Preparare una pozione richiede un giorno. Quando crei una pozione, stabilisci il livello dell'incantatore, che deve essere sufficiente per lanciare l'incantesimo in questione e non superiore al tuo livello. Il prezzo base di una pozione è il suo livello dell'incantesimo × il livello dell'incantesimo × 50 mo. Per preparare una pozione, devi spendere 1/25 di questo prezzo base in PE e usare materie prime per un costo pari alla metà di questo prezzo base.",
    },
    "craft-magic-arms-and-armor": {
        "benefit": "Puoi creare qualsiasi arma, armatura o scudo magico di cui soddisfi i prerequisiti. Potenziare un'arma, un'armatura o uno scudo richiede un giorno per ogni 1.000 mo nel prezzo delle sue caratteristiche magiche. Per potenziare un'arma, un'armatura o uno scudo, devi spendere 1/25 del prezzo totale delle sue caratteristiche in PE e usare materie prime per un costo pari alla metà del prezzo.",
    },
    "craft-rod": {
        "benefit": "Puoi creare qualsiasi verga di cui soddisfi i prerequisiti. Creare una verga richiede un giorno per ogni 1.000 mo nel suo prezzo base. Per creare una verga, devi spendere 1/25 del suo prezzo base in PE e usare materie prime per un costo pari alla metà del suo prezzo base.",
    },
    "craft-staff": {
        "benefit": "Puoi creare qualsiasi bastone di cui soddisfi i prerequisiti. Creare un bastone richiede un giorno per ogni 1.000 mo nel suo prezzo base. Per creare un bastone, devi spendere 1/25 del suo prezzo base in PE e usare materie prime per un costo pari alla metà del suo prezzo base. Un bastone appena creato ha 50 cariche.",
    },
    "craft-wand": {
        "benefit": "Puoi creare una bacchetta di qualsiasi incantesimo di 4° livello o inferiore che conosci. Creare una bacchetta richiede un giorno per ogni 1.000 mo nel suo prezzo base. Il prezzo base di una bacchetta è il suo livello dell'incantatore × il livello dell'incantesimo × 750 mo. Per creare una bacchetta, devi spendere 1/25 di questo prezzo base in PE e usare materie prime per un costo pari alla metà del prezzo base.",
    },
    "craft-wondrous-item": {
        "benefit": "Puoi creare qualsiasi oggetto meraviglioso di cui soddisfi i prerequisiti. Incantare un oggetto meraviglioso richiede un giorno per ogni 1.000 mo nel suo prezzo. Per incantare un oggetto meraviglioso, devi spendere 1/25 del prezzo dell'oggetto in PE e usare materie prime per un costo pari alla metà di questo prezzo. Puoi anche riparare un oggetto meraviglioso rotto se soddisfi i prerequisiti per crearlo.",
    },
    "deceitful": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Camuffare e Falsificare.",
    },
    "deflect-arrows": {
        "benefit": "Devi avere almeno una mano libera (senza tenere nulla) per usare questo talento. Una volta per round, quando saresti normalmente colpito da un'arma a distanza, puoi deviarla in modo da non subire danni. Devi essere consapevole dell'attacco e non essere colto alla sprovvista. Tentare di deviare un'arma a distanza non conta come un'azione. Armi a distanza eccezionalmente massicce e armi a distanza generate da incantesimi o capacità magiche non possono essere deviate.",
        "special": "Un monaco può selezionare Deviare Frecce come talento bonus al 2° livello, anche se non soddisfa i prerequisiti. Un guerriero può selezionare Deviare Frecce come uno dei suoi talenti bonus da guerriero.",
    },
    "deft-hands": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Rapidità di Mano e Usare Corde.",
    },
    "diehard": {
        "benefit": "Quando sei ridotto tra –1 e –9 punti ferita, diventi automaticamente stabile. Non devi tirare d% per vedere se perdi 1 punto ferita ogni round. Quando sei ridotto a punti ferita negativi, puoi scegliere di agire come se fossi disabilitato, anziché morente. Devi prendere questa decisione non appena sei ridotto a punti ferita negativi (anche se non è il tuo turno). Se non agisci, perdi comunque punti ferita come normale.",
        "normal": "Un personaggio senza questo talento che è ridotto tra –1 e –9 punti ferita è incosciente e morente.",
    },
    "diligent": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Valutare e Decifrare Scritti.",
    },
    "empower-spell": {
        "benefit": "Tutti gli effetti numerici variabili di un incantesimo potenziato sono aumentati della metà. I tiri salvezza e i tiri contrapposti non sono influenzati, né lo sono gli incantesimi senza variabili casuali. Un incantesimo potenziato usa uno slot incantesimo di due livelli superiore al livello effettivo dell'incantesimo.",
    },
    "enlarge-spell": {
        "benefit": "Puoi alterare un incantesimo con raggio corto, medio o lungo per aumentare il suo raggio del 100%. Un incantesimo esteso con raggio corto ha ora un raggio di 15 m + 1,5 m/livello, mentre gli incantesimi a raggio medio hanno un raggio di 60 m + 6 m/livello e gli incantesimi a raggio lungo hanno un raggio di 240 m + 24 m/livello. Un incantesimo esteso usa uno slot incantesimo di un livello superiore al livello effettivo dell'incantesimo.",
    },
    "eschew-materials": {
        "benefit": "Puoi lanciare qualsiasi incantesimo che ha una componente materiale del costo di 1 mo o meno senza bisogno di quella componente. (Il lancio dell'incantesimo provoca comunque attacchi di opportunità come normale.) Se l'incantesimo richiede una componente materiale che costa più di 1 mo, devi avere la componente materiale a portata di mano per lanciare l'incantesimo, come normale.",
    },
    "exotic-weapon-proficiency": {
        "benefit": "Effettui i tiri per colpire con l'arma selezionata normalmente.",
        "normal": "Un personaggio che usa un'arma con cui non è competente subisce una penalità di –4 ai tiri per colpire.",
        "special": "Puoi ottenere Competenza nelle Armi Esotiche più volte. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma esotica.",
    },
    "extend-spell": {
        "benefit": "Un incantesimo prolungato dura il doppio del normale. Un incantesimo con durata di concentrazione, istantaneo o permanente non è influenzato da questo talento. Un incantesimo prolungato usa uno slot incantesimo di un livello superiore al livello effettivo dell'incantesimo.",
    },
    "extra-turning": {
        "benefit": "Ogni volta che prendi questo talento, puoi usare la tua capacità di scacciare o intimorire creature quattro volte in più al giorno del normale. Se hai la capacità di scacciare o intimorire più di un tipo di creatura, ciascuna delle tue capacità di scacciare o intimorire ottiene quattro usi aggiuntivi al giorno.",
        "normal": "Senza questo talento, un personaggio può tipicamente scacciare o intimorire non morti (o altre creature) un numero di volte al giorno pari a 3 + il suo modificatore di Carisma.",
        "special": "Puoi ottenere Scacciare Extra più volte. I suoi effetti si cumulano. Ogni volta che prendi il talento, puoi usare ciascuna delle tue capacità di scacciare o intimorire quattro volte aggiuntive al giorno.",
    },
    "far-shot": {
        "benefit": "Quando usi un'arma a proiettile, come un arco, il suo incremento di gittata aumenta della metà (moltiplicato per 1,5). Quando usi un'arma da lancio, il suo incremento di gittata è raddoppiato.",
        "special": "Un guerriero può selezionare Tiro Lontano come uno dei suoi talenti bonus da guerriero.",
    },
    "feat-descriptions--armor-proficiency-heavy": {
        "benefit": "Vedi Competenza nelle Armature (leggere).",
        "normal": "Vedi Competenza nelle Armature (leggere).",
        "special": "Guerrieri, paladini e chierici hanno automaticamente Competenza nelle Armature (pesanti) come talento bonus. Non hanno bisogno di selezionarlo.",
    },
    "feat-descriptions--armor-proficiency-light": {
        "benefit": "Quando indossi un tipo di armatura con cui sei competente, la penalità di controllo dell'armatura per quell'armatura si applica solo alle prove di Equilibrio, Scalare, Artista della Fuga, Nascondersi, Saltare, Muoversi Silenziosamente, Rapidità di Mano e Acrobazia.",
        "normal": "Un personaggio che indossa un'armatura con cui non è competente applica la sua penalità di controllo dell'armatura ai tiri per colpire e a tutte le prove di abilità che comportano movimento, incluso Cavalcare.",
        "special": "Tutti i personaggi eccetto maghi, stregoni e monaci hanno automaticamente Competenza nelle Armature (leggere) come talento bonus. Non hanno bisogno di selezionarlo.",
    },
    "feat-name": {
        "benefit": "Ciò che il talento consente al personaggio (\"tu\" nella descrizione del talento) di fare. Se un personaggio ha lo stesso talento più di una volta, i suoi benefici non si cumulano a meno che non sia indicato diversamente nella descrizione. In generale, avere un talento due volte è uguale ad averlo una volta.",
        "normal": "A cosa è limitato o da cosa è ristretto un personaggio che non ha questo talento. Se non avere il talento non causa alcuno svantaggio particolare, questa voce è assente.",
        "special": "Fatti aggiuntivi sul talento che possono essere utili quando si decide se acquisirlo.",
    },
    "forge-ring": {
        "benefit": "Puoi creare qualsiasi anello di cui soddisfi i prerequisiti. Creare un anello richiede un giorno per ogni 1.000 mo nel suo prezzo base. Per creare un anello, devi spendere 1/25 del suo prezzo base in PE e usare materie prime per un costo pari alla metà del suo prezzo base. Puoi anche riparare un anello rotto se soddisfi i prerequisiti per crearlo.",
    },
    "greater-spell-focus": {
        "benefit": "Aggiungi +1 alla Classe Difficoltà per tutti i tiri salvezza contro gli incantesimi della scuola di magia selezionata. Questo bonus si cumula con il bonus di Focalizzazione Magica.",
        "special": "Puoi ottenere questo talento più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a una nuova scuola di magia a cui hai già applicato il talento Focalizzazione Magica.",
    },
    "greater-spell-penetration": {
        "benefit": "Ottieni un bonus di +2 alle prove di livello dell'incantatore (1d20 + livello dell'incantatore) effettuate per superare la resistenza agli incantesimi di una creatura. Questo bonus si cumula con quello di Penetrazione Magica.",
    },
    "greater-two-weapon-fighting": {
        "benefit": "Ottieni un terzo attacco con la tua arma secondaria, anche se con una penalità di –10.",
        "special": "Un guerriero può selezionare Combattere con Due Armi Superiore come uno dei suoi talenti bonus da guerriero. Un ranger di 11° livello che ha scelto lo stile di combattimento con due armi è considerato come se avesse Combattere con Due Armi Superiore, anche se non ne soddisfa i prerequisiti.",
    },
    "greater-weapon-focus": {
        "benefit": "Ottieni un bonus di +1 a tutti i tiri per colpire effettuati usando l'arma selezionata. Questo bonus si cumula con altri bonus ai tiri per colpire, incluso quello di Focalizzazione sull'Arma.",
        "special": "Puoi ottenere Focalizzazione sull'Arma Superiore più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma.",
    },
    "greater-weapon-specialization": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri per i danni effettuati usando l'arma selezionata. Questo bonus si cumula con altri bonus ai tiri per i danni, incluso quello di Specializzazione sull'Arma.",
        "special": "Puoi ottenere Specializzazione sull'Arma Superiore più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma.",
    },
    "heighten-spell": {
        "benefit": "Un incantesimo intensificato ha un livello dell'incantesimo più alto del normale (fino a un massimo di 9° livello). A differenza di altri talenti metamagici, Incantesimi Intensificati aumenta effettivamente il livello dell'incantesimo che modifica. Tutti gli effetti dipendenti dal livello dell'incantesimo (come le CD dei tiri salvezza e la capacità di penetrare un <i>globo di invulnerabilità inferiore</i>) sono calcolati in base al livello intensificato.",
    },
    "improved-counterspell": {
        "benefit": "Quando controincanti, puoi usare un incantesimo della stessa scuola che sia di uno o più livelli superiore all'incantesimo bersaglio.",
        "normal": "Senza questo talento, puoi controincantare un incantesimo solo con lo stesso incantesimo o con un incantesimo specificamente designato come contromisura dell'incantesimo bersaglio.",
    },
    "improved-familiar": {
        "benefit": "Quando scegli un famiglio, le creature elencate di seguito sono disponibili anche per l'incantatore. L'incantatore può scegliere un famiglio con un allineamento fino a un passo di distanza su ciascuno degli assi di allineamento (da legale a caotico, da buono a malvagio).",
    },
    "improved-feint": {
        "benefit": "Puoi effettuare una prova di Raggirare per fintare in combattimento come azione di movimento.",
        "normal": "Fintare in combattimento è un'azione standard.",
    },
    "improved-precise-shot": {
        "benefit": "I tuoi attacchi a distanza ignorano il bonus alla CA garantito ai bersagli da qualsiasi cosa che non sia copertura totale, e la probabilità di mancamento garantita ai bersagli da qualsiasi cosa che non sia occultamento totale. Copertura totale e occultamento totale forniscono i loro normali benefici contro i tuoi attacchi a distanza. Inoltre, quando spari o lanci un'arma a distanza contro un bersaglio impegnato in lotta, non devi tirare casualmente per vedere quale partecipante alla lotta è colpito.",
        "normal": "Vedi le regole normali sugli effetti di copertura e occultamento. Senza questo talento, un personaggio che spara o lancia un'arma a distanza contro un bersaglio impegnato in lotta deve tirare casualmente per vedere quale partecipante alla lotta è colpito.",
        "special": "Un guerriero può selezionare Tiro Preciso Migliorato come uno dei suoi talenti bonus da guerriero. Un ranger di 11° livello che ha scelto lo stile di combattimento con arco è considerato come se avesse Tiro Preciso Migliorato, anche se non ne soddisfa i prerequisiti.",
    },
    "investigator": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Raccogliere Informazioni e Cercare.",
    },
    "leadership": {
        "benefit": "Avere questo talento consente al personaggio di attrarre compagni leali e seguaci devoti, subordinati che lo assistono. Il personaggio può reclutare un coorteo e un certo numero di seguaci in base al suo punteggio di Autorità.",
    },
    "magical-aptitude": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Conoscenze Magiche e Utilizzare Oggetti Magici.",
    },
    "manyshot": {
        "benefit": "Come azione standard, puoi tirare due frecce contro un singolo avversario entro 9 metri. Entrambe le frecce usano lo stesso tiro per colpire (con una penalità di –4) per determinare il successo e infliggono danni normalmente. Per ogni cinque punti di bonus di attacco base che hai sopra +6, puoi aggiungere una freccia aggiuntiva al tiro, fino a un massimo di quattro frecce (con un bonus di attacco base di +16 o superiore).",
        "special": "Indipendentemente dal numero di frecce che tiri, applichi i danni basati sulla precisione solo una volta. Se ottieni un colpo critico, solo la prima freccia tirata infligge danni critici; tutte le altre infliggono danni normali.",
    },
    "martial-weapon-proficiency": {
        "benefit": "Effettui i tiri per colpire con l'arma selezionata normalmente.",
        "normal": "Quando usi un'arma con cui non sei competente, subisci una penalità di –4 ai tiri per colpire.",
        "special": "Barbari, guerrieri, paladini e ranger sono competenti con tutte le armi da guerra. Non hanno bisogno di selezionare questo talento. Puoi ottenere Competenza nelle Armi da Guerra più volte. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma da guerra.",
    },
    "maximize-spell": {
        "benefit": "Tutti gli effetti numerici variabili di un incantesimo modificato da questo talento sono massimizzati. I tiri salvezza e i tiri contrapposti non sono influenzati, né lo sono gli incantesimi senza variabili casuali. Un incantesimo massimizzato usa uno slot incantesimo di tre livelli superiore al livello effettivo dell'incantesimo.",
    },
    "negotiator": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Diplomazia e Percepire Intenzioni.",
    },
    "nimble-fingers": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Disattivare Congegni e Scassinare Serrature.",
    },
    "persuasive": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Raggirare e Intimidire.",
    },
    "quicken-spell": {
        "benefit": "Lanciare un incantesimo rapido è un'azione gratuita. Puoi effettuare un'altra azione, incluso lanciare un altro incantesimo, nello stesso round in cui lanci un incantesimo rapido. Puoi lanciare solo un incantesimo rapido per round. Un incantesimo il cui tempo di lancio è più di 1 azione di round completo non può essere reso rapido. Un incantesimo rapido usa uno slot incantesimo di quattro livelli superiore al livello effettivo dell'incantesimo.",
        "special": "Questo talento non può essere applicato a nessun incantesimo lanciato spontaneamente (inclusi incantesimi da stregone, bardo e incantesimi da chierico o druido lanciati spontaneamente), poiché applicare un talento metamagico a un incantesimo lanciato spontaneamente ne aumenta automaticamente il tempo di lancio.",
    },
    "rapid-reload": {
        "benefit": "Il tempo necessario per ricaricare il tuo tipo di balestra scelto è ridotto a un'azione gratuita (per una balestra a mano o leggera) o a un'azione di movimento (per una balestra pesante). Ricaricare una balestra provoca comunque un attacco di opportunità. Se hai selezionato questo talento per la balestra a mano o leggera, puoi tirare quella balestra con la stessa velocità con cui potresti tirare un arco.",
        "normal": "Un personaggio senza questo talento ha bisogno di un'azione di movimento per ricaricare una balestra a mano o leggera, o di un'azione di round completo per ricaricare una balestra pesante.",
        "special": "Puoi ottenere Ricarica Rapida più volte. Ogni volta che prendi il talento, si applica a un nuovo tipo di balestra. Un guerriero può selezionare Ricarica Rapida come uno dei suoi talenti bonus da guerriero.",
    },
    "scribe-scroll": {
        "benefit": "Puoi creare una pergamena di qualsiasi incantesimo che conosci. Scrivere una pergamena richiede un giorno per ogni 1.000 mo nel suo prezzo base. Il prezzo base di una pergamena è il suo livello dell'incantesimo × il suo livello dell'incantatore × 25 mo. Per scrivere una pergamena, devi spendere 1/25 di questo prezzo base in PE e usare materie prime per un costo pari alla metà del prezzo base.",
    },
    "shot-on-the-run": {
        "benefit": "Quando usi l'azione di attacco con un'arma a distanza, puoi muoverti sia prima che dopo l'attacco, purché la distanza totale che percorri non sia maggiore della tua velocità.",
        "special": "Un guerriero può selezionare Tiro in Movimento come uno dei suoi talenti bonus da guerriero.",
    },
    "silent-spell": {
        "benefit": "Un incantesimo silenzioso può essere lanciato senza componenti verbali. Gli incantesimi senza componenti verbali non sono influenzati. Un incantesimo silenzioso usa uno slot incantesimo di un livello superiore al livello effettivo dell'incantesimo.",
        "special": "Gli incantesimi da bardo non possono essere potenziati da questo talento metamagico.",
    },
    "simple-weapon-proficiency": {
        "benefit": "Effettui i tiri per colpire con le armi semplici normalmente.",
        "normal": "Quando usi un'arma con cui non sei competente, subisci una penalità di –4 ai tiri per colpire.",
        "special": "Tutti i personaggi eccetto druidi, monaci e maghi sono automaticamente competenti con tutte le armi semplici. Non hanno bisogno di selezionare questo talento.",
    },
    "skill-focus": {
        "benefit": "Ottieni un bonus di +3 a tutte le prove che coinvolgono quell'abilità.",
        "special": "Puoi ottenere questo talento più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a una nuova abilità.",
    },
    "snatch-arrows": {
        "benefit": "Quando usi il talento Deviare Frecce puoi afferrare l'arma invece di deviarla semplicemente. Le armi da lancio possono essere immediatamente rilanciate contro l'attaccante originale (anche se non è il tuo turno) o conservate per un uso successivo. Devi avere almeno una mano libera (senza tenere nulla) per usare questo talento.",
        "special": "Un guerriero può selezionare Afferrare Frecce come uno dei suoi talenti bonus da guerriero.",
    },
    "spell-mastery": {
        "benefit": "Ogni volta che prendi questo talento, scegli un numero di incantesimi pari al tuo modificatore di Intelligenza che già conosci. Da quel momento in poi, puoi preparare questi incantesimi senza fare riferimento a un libro degli incantesimi.",
        "normal": "Senza questo talento, devi usare un libro degli incantesimi per preparare tutti i tuoi incantesimi, eccetto <i>lettura del magico</i>.",
    },
    "still-spell": {
        "benefit": "Un incantesimo immobilizzato può essere lanciato senza componenti somatiche. Gli incantesimi senza componenti somatiche non sono influenzati. Un incantesimo immobilizzato usa uno slot incantesimo di un livello superiore al livello effettivo dell'incantesimo.",
    },
    "tower-shield-proficiency": {
        "benefit": "Puoi usare uno scudo torre e subire solo le penalità standard.",
        "normal": "Un personaggio che usa uno scudo con cui non è competente subisce la penalità di controllo dell'armatura dello scudo ai tiri per colpire e a tutte le prove di abilità che comportano movimento, incluso Cavalcare.",
        "special": "I guerrieri hanno automaticamente Competenza nello Scudo Torre come talento bonus. Non hanno bisogno di selezionarlo.",
    },
    "trample": {
        "benefit": "Quando tenti di travolgere un avversario mentre sei in sella, il bersaglio non può scegliere di evitarti. La tua cavalcatura può effettuare un attacco con zoccolo contro qualsiasi bersaglio che abbatti, ottenendo il bonus standard di +4 ai tiri per colpire contro bersagli proni.",
        "special": "Un guerriero può selezionare Travolgere come uno dei suoi talenti bonus da guerriero.",
    },
    "two-weapon-defense": {
        "benefit": "Quando impugni un'arma doppia o due armi (escluse armi naturali o colpi senz'armi), ottieni un bonus di scudo +1 alla CA. Quando combatti sulla difensiva o usi l'azione di difesa totale, questo bonus di scudo aumenta a +2.",
        "special": "Un guerriero può selezionare Difesa con Due Armi come uno dei suoi talenti bonus da guerriero.",
    },
    "weapon-specialization": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri per i danni effettuati usando l'arma selezionata.",
        "special": "Puoi ottenere questo talento più volte. I suoi effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma. Un guerriero può selezionare Specializzazione sull'Arma come uno dei suoi talenti bonus da guerriero.",
    },
    "widen-spell": {
        "benefit": "Puoi alterare un incantesimo a forma di scoppio, emanazione, linea o diffusione per aumentare la sua area. Qualsiasi misurazione numerica dell'area dell'incantesimo aumenta del 100%. Un incantesimo allargato usa uno slot incantesimo di tre livelli superiore al livello effettivo dell'incantesimo. Gli incantesimi che non hanno un'area di una di queste quattro forme non sono influenzati da questo talento.",
    },
}


# ── Main logic ───────────────────────────────────────────────────────────

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_overlay(overlay, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(overlay, f, ensure_ascii=False, indent=2)
        f.write("\n")


def translate_races(data_dir):
    overlay_path = os.path.join(data_dir, "i18n", "it", "races.json")
    overlay = load_json(overlay_path)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0
    for slug, traits in RACE_TRAITS.items():
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]
        if "traits" not in entry:
            entry["traits"] = traits
            added += 1
        if "desc_html" not in entry and slug in RACE_DESC_HTML:
            entry["desc_html"] = RACE_DESC_HTML[slug]
            added += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)
    print(f"  Races: {added} new translations added")
    return added


def translate_feats(data_dir):
    overlay_path = os.path.join(data_dir, "i18n", "it", "feats.json")
    overlay = load_json(overlay_path)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0

    # Apply benefit/normal/special translations
    for slug, fields in FEAT_TRANSLATIONS.items():
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]
        for field, value in fields.items():
            if field not in entry:
                entry[field] = value
                added += 1

    # Apply prerequisites translations
    for slug, prereq_it in FEAT_PREREQUISITES.items():
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]
        if "prerequisites" not in entry:
            entry["prerequisites"] = prereq_it
            added += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)
    print(f"  Feats: {added} new translations added")
    return added


CATEGORY_HANDLERS = {
    "races": translate_races,
    "feats": translate_feats,
}


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    category_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if category_filter:
        if category_filter not in CATEGORY_HANDLERS:
            print(f"Unknown category: {category_filter}")
            sys.exit(1)
        handlers = {category_filter: CATEGORY_HANDLERS[category_filter]}
    else:
        handlers = CATEGORY_HANDLERS

    total = 0
    for cat, handler in handlers.items():
        total += handler(data_dir)

    print(f"\nTotal: {total} new translations added")


if __name__ == "__main__":
    main()
