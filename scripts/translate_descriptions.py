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


# ── Feat translations (benefit, normal, special) ─────────────────────────
# These are the most commonly used feats with their benefit text translated

FEAT_TRANSLATIONS = {
    "alertness": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Ascoltare e Osservare.",
    },
    "blind-fight": {
        "benefit": "In mischia, ogni volta che manchi a causa dell'occultamento, puoi ritirare la percentuale di mancamento per vedere se effettivamente colpisci. Un attaccante invisibile non ottiene vantaggi ai tiri per colpire contro di te in mischia. Cioè, non perdi il tuo bonus di Destrezza alla Classe Armatura, e l'attaccante non ottiene il solito bonus di +2 per l'invisibilità. Tuttavia, l'attaccante invisibile ottiene ancora il beneficio dell'occultamento totale (50% di probabilità di mancamento). Non hai bisogno di effettuare prove di Acrobazia per muoverti alla velocità piena in oscurità totale.",
        "normal": "La mischia regolare contro un avversario con occultamento richiede una prova di mancamento. I nemici invisibili ottengono vantaggi ai tiri per colpire contro di te in mischia.",
        "special": "Il talento Combattere alla Cieca non ha effetto contro un personaggio che è oggetto di un incantesimo di <i>intermittenza</i>.",
    },
    "cleave": {
        "benefit": "Se colpisci un avversario con sufficiente danno da farlo cadere (tipicamente riducendo i suoi punti ferita sotto 0 o uccidendolo), ottieni un attacco in mischia extra immediato contro un'altra creatura nelle vicinanze. Non puoi fare un passo di 1,5 m prima di effettuare questo attacco extra. L'attacco extra è al tuo bonus di attacco completo, anche se hai già attaccato in quel round. Puoi usare questa capacità una volta per round.",
    },
    "combat-casting": {
        "benefit": "Ottieni un bonus di +4 alle prove di Concentrazione effettuate per lanciare un incantesimo o usare una capacità magica mentre sei sulla difensiva o mentre sei in lotta.",
    },
    "combat-expertise": {
        "benefit": "Quando usi l'azione di attacco o l'azione di attacco completo in mischia, puoi subire una penalità di –1 ai tiri per colpire in mischia e ottenere un bonus di schivare +1 alla Classe Armatura. Questa penalità e bonus aumentano di 1 per ogni –1 nei tiri per colpire, fino a un massimo di –5/+5. Devi scegliere di usare questa capacità prima di effettuare un tiro per colpire, e i suoi effetti durano fino alla tua prossima azione.",
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
    },
    "great-cleave": {
        "benefit": "Questo talento funziona come Fendente, eccetto che non c'è limite al numero di volte che puoi usarlo per round.",
    },
    "great-fortitude": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sulla Tempra.",
    },
    "improved-bull-rush": {
        "benefit": "Quando effettui uno spingere, non provochi un attacco di opportunità dal difensore. Ottieni anche un bonus di +4 alla prova di Forza per spingere.",
    },
    "improved-critical": {
        "benefit": "Quando usi l'arma selezionata, il suo intervallo di minaccia di critico è raddoppiato.",
        "special": "Puoi ottenere Critico Migliorato più volte. Gli effetti non si cumulano. Ogni volta che prendi il talento, si applica a un nuovo tipo di arma. Questo effetto non si cumula con nessun altro effetto che espande l'intervallo di minaccia di un'arma.",
    },
    "improved-disarm": {
        "benefit": "Non provochi un attacco di opportunità quando tenti di disarmare un avversario, né l'avversario ha la possibilità di disarmarti. Ottieni anche un bonus di +4 alla prova di attacco per disarmare il tuo avversario.",
        "normal": "Senza questo talento, tentare di disarmare provoca un attacco di opportunità.",
    },
    "improved-grapple": {
        "benefit": "Non provochi un attacco di opportunità quando effettui un attacco di contatto per iniziare una lotta. Ottieni anche un bonus di +4 a tutte le prove di lotta, indipendentemente dal fatto che tu abbia iniziato la lotta o meno.",
        "normal": "Senza questo talento, effettuare una lotta provoca un attacco di opportunità.",
    },
    "improved-initiative": {
        "benefit": "Ottieni un bonus di +4 alle prove di iniziativa.",
        "special": "Un guerriero può selezionare Iniziativa Migliorata come uno dei suoi talenti bonus da guerriero.",
    },
    "improved-overrun": {
        "benefit": "Quando tenti di travolgere un avversario, il bersaglio non può scegliere di evitarti. Ottieni anche un bonus di +4 alla prova di Forza per abbattere il tuo avversario.",
        "normal": "Senza questo talento, il bersaglio di un travolgimento può scegliere di farsi da parte.",
    },
    "improved-shield-bash": {
        "benefit": "Quando effettui un colpo con lo scudo, puoi comunque applicare il bonus dello scudo alla CA.",
        "normal": "Senza questo talento, un personaggio che effettua un colpo con lo scudo perde il bonus dello scudo alla CA fino alla sua prossima azione.",
    },
    "improved-sunder": {
        "benefit": "Quando colpisci un oggetto tenuto o indossato con un attacco per distruggere, non provochi un attacco di opportunità. Ottieni anche un bonus di +4 alla prova di attacco per distruggere.",
        "normal": "Senza questo talento, tentare di distruggere un oggetto provoca un attacco di opportunità.",
    },
    "improved-trip": {
        "benefit": "Non provochi un attacco di opportunità quando tenti di sgambettare un avversario mentre sei in mischia. Ottieni anche un bonus di +4 alla prova di Forza per sgambettare. Se sgambetti con successo un avversario, ottieni immediatamente un attacco in mischia contro quell'avversario come se non avessi usato il tuo attacco per lo sgambetto.",
        "normal": "Senza questo talento, tentare uno sgambetto provoca un attacco di opportunità.",
    },
    "improved-turning": {
        "benefit": "Aggiungi un bonus di +1 al tuo livello di scacciare quando fai una prova di scacciare per determinare il Dado Vita massimo della creatura non morta che puoi influenzare.",
    },
    "improved-two-weapon-fighting": {
        "benefit": "Oltre al normale attacco extra con un'arma secondaria, ottieni un secondo attacco con essa, anche se con una penalità di –5.",
        "normal": "Senza questo talento, puoi ottenere solo un singolo attacco extra con un'arma secondaria.",
    },
    "improved-unarmed-strike": {
        "benefit": "Sei considerato armato anche quando sei disarmato—cioè, non provochi attacchi di opportunità da avversari armati quando li attacchi disarmato. Tuttavia, provochi ancora attacchi di opportunità come normale se effettui un attacco disarmato quando minacciato da un avversario che non stai attaccando.",
        "normal": "Senza questo talento, sei considerato disarmato quando attacchi con un colpo senz'armi e provochi un attacco di opportunità da avversari armati.",
    },
    "iron-will": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sulla Volontà.",
    },
    "lightning-reflexes": {
        "benefit": "Ottieni un bonus di +2 a tutti i tiri salvezza sui Riflessi.",
    },
    "mobility": {
        "benefit": "Ottieni un bonus di schivare +4 alla Classe Armatura contro attacchi di opportunità causati dal muoversi fuori da o dentro un'area minacciata. Un bonus di schivare di questo tipo non si applica se perdi il tuo bonus di Destrezza alla CA.",
    },
    "mounted-archery": {
        "benefit": "La penalità che subisci quando usi un'arma a distanza mentre sei in sella è dimezzata: –2 invece di –4 se la cavalcatura compie un doppio movimento, e –4 invece di –8 se la cavalcatura corre.",
    },
    "mounted-combat": {
        "benefit": "Una volta per round quando la tua cavalcatura è colpita in combattimento, puoi tentare una prova di Cavalcare (come reazione) per negare il colpo. La prova di Cavalcare sostituisce la CA della cavalcatura. Se il risultato della tua prova di Cavalcare è maggiore del tiro per colpire, il colpo manca.",
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
    },
    "quick-draw": {
        "benefit": "Puoi estrarre un'arma come azione gratuita invece che come azione di movimento. Puoi lanciare armi alla massima velocità di attacco (molto simile alla penalità per gli attacchi in mischia).",
        "normal": "Senza questo talento, puoi estrarre un'arma come azione di movimento, o (se il tuo bonus di attacco base è +1 o superiore) come azione gratuita come parte di un movimento.",
    },
    "rapid-shot": {
        "benefit": "Puoi ottenere un attacco a distanza extra per round. Tutti i tuoi tiri per colpire per il round subiscono una penalità di –2 quando usi Tiro Rapido.",
    },
    "ride-by-attack": {
        "benefit": "Quando sei in sella e usi l'azione di carica, puoi muoverti e attaccare come con una carica standard e poi continuare a muoverti (fino al doppio della velocità della cavalcatura). Devi muoverti almeno di 3 metri prima e dopo l'attacco.",
    },
    "run": {
        "benefit": "Quando corri, ti muovi a cinque volte la tua velocità normale (se indossi armatura media, leggera o nessuna e trasporti un carico non più che medio) o a quattro volte la tua velocità (se indossi armatura pesante o trasporti un carico pesante). Se effettui un salto dopo una rincorsa, ottieni un bonus di +4 alla prova di Saltare.",
    },
    "self-sufficient": {
        "benefit": "Ottieni un bonus di +2 a tutte le prove di Guarire e Sopravvivenza.",
    },
    "shield-proficiency": {
        "benefit": "Puoi usare uno scudo e non subire la penalità all'attacco associata.",
        "normal": "Quando usi uno scudo con cui non sei competente, subisci la penalità di controllo dell'armatura dello scudo ai tiri per colpire e a tutte le prove di abilità che comportano movimento.",
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
    },
    "spring-attack": {
        "benefit": "Quando usi l'azione di attacco con un'arma da mischia, puoi muoverti sia prima che dopo l'attacco, purché la distanza totale che percorri non sia maggiore della tua velocità. Muoversi in questo modo non provoca un attacco di opportunità dal difensore che stai attaccando.",
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
    },
    "two-weapon-fighting": {
        "benefit": "Le tue penalità al combattimento con due armi sono ridotte di 2 con l'arma primaria e di 6 con l'arma secondaria.",
        "normal": "Se impugni una seconda arma nella mano secondaria, puoi ottenere un attacco extra con quell'arma al costo di una penalità di –6 ai tiri per colpire con l'arma primaria e una penalità di –10 con l'arma secondaria.",
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
    for slug, fields in FEAT_TRANSLATIONS.items():
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]
        for field, value in fields.items():
            if field not in entry:
                entry[field] = value
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
