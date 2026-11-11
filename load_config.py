import os
import yaml
from typing import Dict, Any

def lire_config_yaml(chemin_fichier: str) -> Dict[str, Any]:
    """
    Loads a YAML configuration file and returns its contents as a dictionary.
    """
    try:
        with open(chemin_fichier, 'r', encoding='utf8') as f:
            config_data = yaml.safe_load(f) or {}

        #In our case, mail config file separated
        mail_file = config_data.get('mail_file')
        if mail_file:
            base_dir = os.path.dirname(os.path.abspath(chemin_fichier))
            mail_path = os.path.join(base_dir, mail_file)
            try:
                with open(mail_path, 'r', encoding='utf8') as mf:
                    mail_data = yaml.safe_load(mf) or {}
                config_data['mail'] = mail_data
            except FileNotFoundError:
                print(f"Warning mail file Not Found : {mail_path}")
            except yaml.YAMLError as exc:
                print(f" Error occured while parsing file ({mail_path}) : {exc}")

        return config_data

    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration n'a pas été trouvé à {chemin_fichier}")
        return {}
    except yaml.YAMLError as exc:
        print(f"Erreur lors du parsing YAML : {exc}")
        return {}
