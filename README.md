# Lenovo SN730 Linux Updater

**Partagé par Gérard Huret, alias gg31, pour rendre service à la communauté.**

Petit outil communautaire pour une transition précise du firmware d'un SSD
Lenovo/Western Digital SN730 sous Linux, en gardant l'image officielle intacte.
Code et documentation sous licence MIT ; aucun firmware fourni.

## Statut : expérimental, un cas matériel testé

La méthode a été exécutée avec succès le 18 octobre 2026 sur **un exemplaire** :

| Élément | Cas testé |
| --- | --- |
| SSD | `WDC PC SN730 SDBQNTY-256G-1001` |
| Ancien firmware | `11110101`, slot 1 |
| Nouveau firmware | `11170101`, slot 2 |
| Linux | Ubuntu 24.04 LTS, noyau 6.8, nvme-cli 2.8 |
| Résultat observé | Écriture acceptée, activation après redémarrage, nouvelle version active relue, ancien slot conservé |

Le wrapper public a été adapté pour supprimer les identifiants privés et ajouter
des contrôles génériques ; ses tests unitaires utilisent un contrôleur simulé.
Cela ne remplace pas des essais matériels supplémentaires du wrapper public.
**Pas de validation universelle, de certification constructeur, ni de garantie
que cette mise à jour résolve un problème de démarrage particulier.**

## Retour d'expérience : blocage au logo Lenovo avec un WD SN730

Cas rapporté par **Gérard Huret, alias gg31**, le 18 octobre 2026,
pour aider les personnes rencontrant un symptôme comparable.

### Symptôme et tests croisés

Sur un **ThinkCentre M920q Tiny, modèle 10RS003RFR (type 10RS), Core i5-9500T**, avec le
BIOS `M1UKT79A`, le WD SN730 256 Go en firmware `11110101` était associé
à un blocage au logo Lenovo : même l'accès au BIOS par **F1** ne répondait
plus lors des essais concernés. Il ne s'agissait donc pas seulement d'un
message d'erreur de l'amorçage de Batocera.

Les observations suivantes ont orienté le diagnostic :

- Le BIOS redevenait accessible une fois le WD retiré.
- Un autre NVMe Samsung permettait à cette machine de passer ce blocage.
- Le WD fonctionnait dans un second M920q, modèle **10RS002AFR**, équipé d'un Core i5-8500T,
  ce qui a permis de sauvegarder son contenu puis de préparer Ubuntu
  et la mise à jour depuis cet autre ordinateur.
- Un problème distinct de perte d'heure et de double démarrage avait été
  traité par remplacement de la pile CMOS ; le blocage avec le WD persistait
  ensuite, avant sa mise à jour.

### Intervention et résultat observé

Après sauvegarde, le WD a reçu l'image officielle Lenovo `11170101` sous
Ubuntu sur le second ordinateur. La version active a été relue après un
redémarrage propre, avec l'ancien firmware conservé dans l'autre slot et
aucune erreur média SMART signalée.

Le WD a ensuite été replacé dans le M920q i5-9500T qui bloquait auparavant :
**la machine a dépassé le logo Lenovo et démarré Ubuntu**, selon le test
physique rapporté par Gérard. Ce démarrage ne constitue pas une validation
du retour à Batocera : le WD contenait alors Ubuntu, et non l'installation
Batocera d'origine.

### Ce que ce cas permet — et ne permet pas — de conclure

Le résultat est **compatible avec la résolution d'une interaction entre le
firmware du SSD et le démarrage UEFI**. Mais il s'agit d'un seul exemplaire,
pas d'un essai contrôlé isolant chaque variable : le système installé et
d'autres éléments de configuration ont également changé durant le diagnostic.
La cause exacte n'est donc pas démontrée.

La [notice Lenovo FWNVA70](https://download.lenovo.com/pccbbs/mobiles/fwnva70.txt)
référence `11170101` pour ce SN730, mais ne fournit pas de description précise
des correctifs propres à la transition `11110101` vers `11170101`. Nous ne
présentons pas ce blocage comme un défaut officiellement reconnu par Lenovo,
ni le flash comme une solution garantie pour tous les M920q ou SN730.

**Un blocage au logo ne suffit pas à justifier un flash.** Vérifier le modèle
exact, le firmware, la sauvegarde et les autres causes matérielles avant
toute intervention. Ne pas forcer l'installation sur une autre variante.

## Risques et limites

- Un flash peut rendre un SSD inutilisable. Une coupure, un bogue ou une
  incompatibilité peut entraîner la perte de données ou de l'accès au système.
- Avoir une sauvegarde complète, vérifiée, restaurable et un système de secours
  déjà démarré avec succès. Un deuxième slot ne garantit pas la récupération.
- Utiliser une alimentation secteur stable ; ne pas couper l'alimentation.
- Ce n'est **pas** l'installateur Windows Lenovo : c'est une méthode Linux
  communautaire utilisant les commandes NVMe standard. L'image est officielle,
  mais cette procédure Linux n'est pas présentée comme approuvée par Lenovo.
- Ne pas employer le firmware Dell ou un autre firmware portant un nom proche.
- Seuls le modèle et la transition ci-dessus sont acceptés. Les variantes de
  capacité, de modèle, de firmware, de slots et de granularité sont refusées.
- Aucun formatage, changement de partition, reset à chaud ou redémarrage n'est
  effectué par ces scripts. Aucun programme Windows n'est exécuté.
- Aucun `--force`, aucun contournement de refus du contrôleur, aucune télémétrie.

## Prérequis et téléchargement local

Récupérer le code de ce dépôt, puis se placer dans son dossier :

```sh
git clone https://github.com/eveetesla-bot/lenovo-sn730-linux-updater.git
cd lenovo-sn730-linux-updater
```

### Firmware officiel : provenance et empreintes

Il s'agit du **firmware du SSD**, pas du BIOS Lenovo `M1UKT79A`.
Le BIOS et le firmware du SSD sont deux composants distincts ; ces scripts
ne mettent pas à jour le BIOS.

- Paquet source : [Lenovo FWNVA70, téléchargement officiel](https://download.lenovo.com/pccbbs/mobiles/fwnva70.exe).
- Instructions et historique : [notice Lenovo FWNVA70](https://download.lenovo.com/pccbbs/mobiles/fwnva70.txt).
- Image extraite pour ce cas : `WDC/11170101.fluf`, **2 588 672 octets**.
- Correspondance du profil fournisseur : modèle exact `WDC PC SN730 SDBQNTY-256G-1001`, version source `11110101`, cible `11170101`.

Empreintes SHA256 des fichiers testés (également contrôlées par les scripts) :

```text
fwnva70.exe
c030171d1bb5e65b8f9b9bcd0234ba0d805f2635f6e96a5951b78064347f9a90

11170101.fluf
2dc6487beb9829a30af8c2737513139d211245e07670d2b5993f4a96d0e2b499

fwwinsd.pro
85909f5c7f1198ef9d3bc93732448f381a27f58f1fcac9b9deefdd25a62cc4fb
```

Les binaires et le profil propriétaires ne sont **pas redistribués** dans ce
dépôt et ne relèvent pas de sa licence MIT. Le script les récupère chez Lenovo
et les extrait localement sans modifier le firmware. Respecter les conditions
du constructeur ; la disponibilité d'un téléchargement ne constitue pas une
autorisation de redistribution. Si le téléchargement disparaît ou si une
empreinte diffère, s'arrêter : ne pas remplacer les hashes pour contourner le
contrôle et ne pas utiliser un miroir non vérifié.

### Préparer les outils et extraire le paquet

Python 3.10 ou plus récent, Linux, `nvme-cli`, `innoextract`, sauvegarde et accès
administrateur. Sur Ubuntu :

```sh
sudo apt install python3 nvme-cli innoextract
python3 prepare_firmware.py
```

Le préparateur télécharge le paquet Lenovo FWNVA70, vérifie son SHA256, puis
l'extrait **sans l'exécuter**. Le paquet testé avait une signature Authenticode
Lenovo valide sous Windows ; le préparateur Linux contrôle son hash exact,
mais **ne réalise pas lui-même de vérification Authenticode**.

Les chemins du firmware et du profil sont affichés. Affecter ces chemins à
`FW` et `PROFILE` pour les commandes suivantes, sans les modifier :

```sh
FW='work/extracted/code$GetExtractPath$/WDC/11170101.fluf'
PROFILE='work/extracted/code$GetExtractPath$/fwwinsd.pro'
SSD_SERIAL='VOTRE_NUMERO_DE_SERIE'
```

Identifier **son propre** contrôleur et numéro de série avec `sudo nvme list`
et `sudo nvme id-ctrl /dev/nvme0`. `/dev/nvme0` n'est qu'un exemple : ne pas
supposer que c'est le bon disque. Le script refuse les namespaces et partitions.
Ne pas publier son numéro de série ou ses journaux bruts.

## 1. Contrôle sans écriture — mode par défaut

```sh
sudo python3 sn730_update.py --device /dev/nvme0 --expected-serial "$SSD_SERIAL" \
  --firmware "$FW" --profile "$PROFILE"
```

Contrôle du modèle, de la série saisie localement, des versions, du SMART,
des deux slots, de la granularité, des SHA256 et de la correspondance dans
la table fournisseur. Il ne s'agit pas d'un test d'écriture ni d'une garantie.

## 2. Écriture dans le slot inactif, sans activation

Après sauvegarde et lecture des risques :

```sh
sudo python3 sn730_update.py --device /dev/nvme0 --expected-serial "$SSD_SERIAL" \
  --firmware "$FW" --profile "$PROFILE" --action stage --apply \
  --acknowledge-backup --acknowledge-stable-power --acknowledge-experimental-method
```

Le slot 2 doit être vide. Le slot 1 n'est pas réécrit. Le contrôleur valide et
stocke l'image avec l'action NVMe 0 ; le script vérifie qu'il annonce `11170101`
dans le slot 2 et que le slot 1 reste actif. **Ne pas répéter cette étape.**

## 3. Programmer l'activation au prochain redémarrage

```sh
sudo python3 sn730_update.py --device /dev/nvme0 --expected-serial "$SSD_SERIAL" \
  --firmware "$FW" --profile "$PROFILE" --action activate --apply \
  --acknowledge-backup --acknowledge-stable-power --acknowledge-experimental-method
```

Cela utilise l'action NVMe 2, sans activation à chaud. Le script ne redémarre
pas. Prévoir l'accès au système de secours et effectuer ensuite un redémarrage
propre. Une extinction/réinitialisation peut être requise selon le contrôleur ;
ne pas réinitialiser un contrôleur actif à la main.

## 4. Vérifier après redémarrage

```sh
sudo python3 sn730_update.py --device /dev/nvme0 --expected-serial "$SSD_SERIAL" --action verify
```

Le résultat n'est validé que si Identify Controller indique `11170101`, le
slot 2 est actif sans activation en attente, l'ancien slot 1 est conservé et
le SMART ne signale pas d'alerte critique ou d'erreur média.

## En cas de refus ou d'erreur

**S'arrêter.** Ne pas modifier les hashes, les garde-fous, les versions, le modèle
ou les options de forçage pour faire passer un autre cas. Ne pas relancer
aveuglément après une écriture partielle. Relever d'abord l'état des slots et
faire examiner le résultat par une personne compétente.

Les écritures produisent des journaux **locaux**, privés, dans `logs/`.
Ils contiennent le numéro de série réel : ne pas les joindre à une issue sans
les anonymiser. Le dépôt ignore les journaux et les fichiers du constructeur.

## Tests sans matériel

```sh
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
```

Ces tests simulent les contrôles et commandes ; ils ne doivent jamais accéder
au matériel ni écrire un firmware. Les garde-fous ne dépendent pas d'`assert`.

## Sources primaires

- [Notice Lenovo FWNVA70](https://download.lenovo.com/pccbbs/mobiles/fwnva70.txt)
- [Paquet officiel Lenovo](https://download.lenovo.com/pccbbs/mobiles/fwnva70.exe)
- [NVMe Firmware Download](https://github.com/linux-nvme/nvme-cli/blob/master/Documentation/nvme-fw-download.txt)
- [NVMe Firmware Commit et actions](https://github.com/linux-nvme/nvme-cli/blob/master/Documentation/nvme-fw-commit.txt)
- [Comportement du plugin NVMe de fwupd](https://fwupd.github.io/libfwupdplugin/nvme-README.html)

Merci aux projets nvme-cli et innoextract et à leurs contributeurs. Ce projet
communautaire n'est affilié ni à Lenovo ni à Western Digital. Aucun firmware,
profil propriétaire, accès privé ou journal matériel personnel n'est publié.
