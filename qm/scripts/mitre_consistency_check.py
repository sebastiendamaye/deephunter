"""
This script checks the consistency of MITRE ATT&CK techniques in DeepHunter with the latest data
from the MITRE repository.
It identifies missing techniques, name mismatches, revoked and deprecated techniques, and allows
for interactive updates (if called with "--script-args interactive").
Note that interactive updates are not applied to the deprecated and outdated techniques.

Usage:
./manage.py runscript mitre_consistency_check
./manage.py runscript mitre_consistency_check --script-args interactive
"""

import requests
import re
from django.shortcuts import get_object_or_404
from django.conf import settings
from qm.models import MitreTechnique, MitreTactic

PROXY = settings.PROXY

def str2tactic(s):
    """
    Resolve a MITRE tactic phase name (e.g. "defense-evasion") to its
    MitreTactic object, matching case-insensitively and treating hyphens as
    spaces.

    Returns None if no matching tactic exists in DeepHunter. MITRE occasionally
    adds or renames tactics (e.g. the ATT&CK v18 split of Defense Evasion into
    Stealth + Defense Impairment); when that happens the tactic is unknown here
    until the MitreTactic table is updated. Returning None (instead of raising)
    lets the caller warn-and-skip that tactic rather than aborting the whole run.
    """
    s = s.strip().lower().replace('-', ' ')
    return MitreTactic.objects.filter(name__iexact=s).first()


def resolve_tactics(tactics_str):
    """
    Resolve a comma-separated MITRE phase-name string into (tactics, unknown):
      - tactics: list of matching MitreTactic objects (for the ones that exist)
      - unknown: list of raw phase names with no matching MitreTactic

    Unknown tactics are reported so the caller can warn about them without
    crashing (see str2tactic).
    """
    tactics, unknown = [], []
    for name in tactics_str.split(','):
        tactic = str2tactic(name)
        if tactic is None:
            unknown.append(name.strip())
        else:
            tactics.append(tactic)
    return tactics, unknown

def find_parent_technique(mitre_id):
    """
    Find the parent technique for a given sub-technique ID.

    Returns None if the ID is not a sub-technique, or if the parent technique
    does not (yet) exist in DeepHunter. The parent can legitimately be absent
    when both a new sub-technique and its parent are missing (MITRE added them
    together); returning None (instead of raising) lets the caller display or
    create the sub-technique without aborting the whole run. In interactive
    mode, list_missing is processed in sorted ID order so a missing parent is
    created before its sub-techniques and will resolve on that pass.
    """
    if '.' in mitre_id:
        parent_id = mitre_id.split('.')[0]
        return MitreTechnique.objects.filter(mitre_id=parent_id).first()
    return None

def remove_markdown(text):
    """
    Remove markdown formatting from the text.
    Description in MITRE ATT&CK techniques often contains markdown formatting
    """
    # Remove links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # remove citations (Citation: ...)
    text = re.sub(r'\(Citation: [^\)]+\)', '', text)
    # remove code formatting (``text`)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    return text

def extract_depreciation_comment(text):
    """
    When a technique is deprecated, the description field contains a comment
    about the deprecation. This function extracts that comment.
    """
    match = re.search(r'\*\*(.*?)\*\*', text)
    return match.group(1)

def updated_mitre_id(mitre_id):
    r=requests.get(
        f'https://attack.mitre.org/techniques/{mitre_id.replace(".", "/")}/',
        proxies=PROXY
        )
    if '<meta http-equiv="refresh" content="0; url=/techniques/' in r.text:
        match = re.search(r'url=/techniques/([^"]+)', r.text)
        return match.group(1).replace('/', '.')
    else:
        return mitre_id

def run(*args):

    # check if script called with "interactive" argument
    interactive = True if 'interactive' in args else False
    # Track if changes were applied to display conditionnal message at the end
    changes_applied = False

    # URL of the remote JSON data
    url = 'https://raw.githubusercontent.com/mitre/cti/refs/heads/master/enterprise-attack/enterprise-attack.json'

    response = requests.get(
        url,
        proxies=PROXY
        )

    if response.status_code == 200:

        update_description = False
        list_missing = []
        list_name_changed = []
        list_revoked = []
        list_deprecated = []
        mitre_new_ref = []
        list_to_remove = []

        if not interactive:
            print("\nYou can run the script in interactive mode by using the following command:")
            print("./manage.py runscript mitre_consistency_check --script-args interactive")


        data = response.json()
        mitre_techniques = [item for item in data['objects'] if item['type'] == 'attack-pattern']

        for technique in mitre_techniques:
            if technique['external_references']:
                for source in technique['external_references']:
                    if source['source_name'] == 'mitre-attack':

                        revoked = False
                        deprecated = False
                        if 'revoked' in technique:
                            revoked = technique['revoked']
                        deprecated = technique['x_mitre_deprecated']

                        mitre_new_ref.append({
                            'mitre_id': source['external_id'],
                            'name': technique['name'],
                            'revoked': revoked,
                            'deprecated': deprecated,
                            'description': remove_markdown(technique['description']),
                        })

                        try:
                            # Check if the technique exists in DeepHunter
                            ttp = get_object_or_404(MitreTechnique, mitre_id=source['external_id'])
                            if revoked:
                                list_revoked.append({
                                    'mitre_id': ttp.mitre_id,
                                    'name': ttp.name,
                                    'updated_mitre_id': updated_mitre_id(ttp.mitre_id)
                                    })
                            if deprecated:
                                list_deprecated.append({
                                    'mitre_id': ttp.mitre_id,
                                    'name': ttp.name,
                                    'description': extract_depreciation_comment(technique['description'])
                                    })

                            # Check name consistency
                            if ttp.name.strip() != technique['name'].strip():
                                list_name_changed.append({
                                    'mitre_id': ttp.mitre_id,
                                    'name': ttp.name,
                                    'new_name': technique['name']
                                    })
                                                        
                        except Exception as e:

                            # Technique not found in DeepHunter
                            if not revoked and not deprecated:
                                # Missing MITRE TTP in DeepHunter
                                list_missing.append({
                                    'id': source['external_id'],
                                    'name': technique['name'],
                                    'subtechnique': technique['x_mitre_is_subtechnique'],
                                    'description': technique['description'],
                                    'tactics': ','.join(tactic['phase_name'] for tactic in technique['kill_chain_phases'])
                                    })

                                # in case of a sub-technique, we search if the technique exists. Else, it needs to be created
                                if technique['x_mitre_is_subtechnique']:
                                    if not MitreTechnique.objects.filter(mitre_id=source['external_id'].split('.')[0]).exists():
                                        # parent doesn't exist either, so we create it if it's not already in the list
                                        if not any(item['id'] == source['external_id'] for item in list_missing):
                                            list_missing.append({
                                                'id': source['external_id'],
                                                'name': technique['name'],
                                                'subtechnique': technique['x_mitre_is_subtechnique'],
                                                'description': '',
                                                'tactics': ','.join(tactic['phase_name'] for tactic in technique['kill_chain_phases'])
                                                })

        # Check in DeepHunter if there is any TTP that is not in the MITRE list
        for ttp in MitreTechnique.objects.all():
            if not any(i['mitre_id'] == ttp.mitre_id for i in mitre_new_ref):
                list_to_remove.append({"id": ttp.mitre_id, "name": ttp.name})


        # Print the results
        if list_to_remove:
            print("\n====================================")
            print("INVALID (SUB)TECHNIQUES (likely mispelled)")
            print("====================================")
            print(f"{'MITRE ID':<10} | {'Name':<50}")
            print("-" * 100)
            for item in list_to_remove:
                print(f"{item['id']:<10} | {item['name']:<50}")
            print("-" * 100)

            if interactive:
                r = input("\nShould I remove these techniques from DeepHunter? (y/N): ").lower()
                if r == 'y' or r == 'yes':
                    changes_applied = True
                    for item in list_to_remove:
                        technique = get_object_or_404(MitreTechnique, mitre_id=item['id'])
                        technique.delete()
                    print("[DONE]")


        if list_missing:
            list_missing = sorted(list_missing, key=lambda x: x['id'])
            print("\n====================================")
            print("MISSING (SUB)TECHNIQUES")
            print("====================================")
            print(f"{'MITRE ID':<10} | {'Name':<50} | {'Sub.':<5} | {'Parent':<7} | {'Tactics':<30} | {'Warnings':<50}")
            print("-" * 200)
            for item in list_missing:
                tactic_objs, unknown_tactics = resolve_tactics(item['tactics'])
                tactics = ','.join(t.mitre_id for t in tactic_objs)
                parent_technique_id = ''
                parent_missing = False
                if item['subtechnique']:
                    parent_technique = find_parent_technique(item['id'])
                    if parent_technique is None:
                        # Parent not in DeepHunter yet (likely also in list_missing).
                        parent_technique_id = item['id'].split('.')[0]
                        parent_missing = True
                    else:
                        parent_technique_id = parent_technique.mitre_id
                # Warnings: check if the name already exists in DeepHunter
                warnings = ''
                if MitreTechnique.objects.filter(name=item['name']).exists():
                    t = get_object_or_404(MitreTechnique, name=item['name'])
                    warnings += f"Name already exists in DeepHunter ({t.mitre_id})"
                if parent_missing:
                    warnings += f"{'; ' if warnings else ''}Parent {parent_technique_id} not yet in DeepHunter"
                if unknown_tactics:
                    warnings += f"{'; ' if warnings else ''}Unknown tactic(s), not in DeepHunter: {', '.join(unknown_tactics)}"
                print(f"{item['id']:<10} | {item['name']:<50} | {item['subtechnique']:<5} | {parent_technique_id:<7} | {tactics:<30} | {warnings:<50}")
            print("-" * 200)

            if interactive:
                r = input("\nShould I create these techniques in DeepHunter? (y/N): ").lower()
                if r == 'y' or r == 'yes':
                    changes_applied = True
                    for item in list_missing:
                        tactic_objs, unknown_tactics = resolve_tactics(item['tactics'])
                        # Resolve the parent once. list_missing is sorted by ID, so a
                        # missing parent (e.g. T1027) is created before its
                        # sub-techniques (e.g. T1027.018) and resolves on this same pass.
                        parent_technique = find_parent_technique(item['id']) if item['subtechnique'] else None

                        # first create technique
                        technique = MitreTechnique(
                            mitre_id = item['id'],
                            name = item['name'],
                            is_subtechnique = item['subtechnique'],
                            mitre_technique=parent_technique,
                            description=remove_markdown(item['description'])
                        )
                        technique.save()
                        if item['subtechnique'] and parent_technique is None:
                            print(f"  [WARN] {item['id']}: created without a parent "
                                  f"({item['id'].split('.')[0]} not in DeepHunter)")

                        # we add the tactics (have to be done after, as this is a ManyToMany field).
                        # Unknown tactics (not yet in DeepHunter) are skipped with a warning rather
                        # than aborting the run; add them to the MitreTactic table and re-run to link.
                        for tactic in tactic_objs:
                            technique.mitre_tactic.add(tactic)
                        if unknown_tactics:
                            print(f"  [WARN] {item['id']}: skipped unknown tactic(s) not in DeepHunter: {', '.join(unknown_tactics)}")

                    print("[DONE]")

        if list_name_changed:
            print("\n====================================")
            print("(SUB)TECHNIQUE NAME MISMATCH")
            print("====================================")
            print(f"{'MITRE ID':<10} | {'Current Name':<65} | {'New Name':<65} | {'Verdict':<50}")
            print("-" * 200)
            for item in list_name_changed:

                # Check if name found in the new MITRE references
                found = False
                for i in mitre_new_ref:
                    if i['name'] == item['name'] and not i['revoked'] and not i['deprecated']:
                        found = True
                        break

                if found:
                    verdict = f"Found in: {i['mitre_id']}"
                else:
                    verdict = 'Name likely updated'
                print(f"{item['mitre_id']:<10} | {item['name']:<65} | {item['new_name']:<65} | {verdict:<50}")
            print("-" * 200)

            if interactive:
                r = input("\nShould I update names in DeepHunter? (y/N): ").lower()
                if r == 'y' or r == 'yes':
                    changes_applied = True
                    for item in list_name_changed:
                        analytic = get_object_or_404(MitreTechnique, mitre_id=item['mitre_id'])
                        analytic.name = item['new_name']
                        analytic.save()

                    print("[DONE]")


        if list_revoked:
            print("\n====================================")
            print("REVOKED (SUB)TECHNIQUES")
            print("====================================")
            print(f"{'MITRE ID':<10} | {'Name':<50} | {'Updated MITRE ID':<10}")
            print("-" * 200)
            for item in list_revoked:
                updated_mitre_message = ''
                #check if updated MITRE ID exists in DeepHunter
                found = True if MitreTechnique.objects.filter(mitre_id=item['updated_mitre_id']).exists() else False
                if found:
                    updated_mitre_message += " (already exists in DeepHunter)"
                if any(i['mitre_id'] == item['updated_mitre_id'] for i in list_name_changed):
                    updated_mitre_message += " (appears in tech mismatch list)"
                print(f"{item['mitre_id']:<10} | {item['name']:<50} | {item['updated_mitre_id']:<10} {updated_mitre_message}")
            print("-" * 200)


        if list_deprecated:
            print("\n====================================")
            print("DEPRECATED SUB(TECHNIQUES)")
            print("====================================")
            print(f"{'MITRE ID':<10} | {'Name':<50} | {'Comments':<150}")
            print("-" * 200)
            for item in list_deprecated:
                print(f"{item['mitre_id']:<10} | {item['name']:<50} | {item['description']:<150}")
            print("-" * 200)


        # check if description field should be updated
        if interactive:
            if not (list_missing or list_name_changed or list_revoked or list_deprecated or list_to_remove):
                print('\nThe local MITRE tables in DeepHunter seem consistent.')
                r = input("Would you like to update the description field for all techniques with the latest information available? (y/N): ").lower()
                if r == 'y' or r == 'yes':
                    for t in mitre_new_ref:
                        # Update the description
                        tech = get_object_or_404(MitreTechnique, mitre_id=t['mitre_id'])
                        tech.description = t['description']
                        tech.save()
                    print("[DONE]")


        if changes_applied:
            r = requests.get(
                'https://api.github.com/repos/mitre-attack/attack-stix-data/releases/latest',
                proxies=PROXY
            )
            version = r.json()['tag_name']
            print("\nDon't forget to update the version of MITRE in DeepHunter.")
            print(f"Latest MITRE version: {version}")

    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")