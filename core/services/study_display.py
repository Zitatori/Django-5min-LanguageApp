def localized_study_content(content, language):
    if not language or not language.startswith('fr'):
        return content
    if isinstance(content, str):
        return content.replace('Questions en W', 'Questions avec où, quand, combien de temps')
    if isinstance(content, list):
        return [localized_study_content(item, language) for item in content]
    if isinstance(content, dict):
        return {key: localized_study_content(value, language) for key, value in content.items()}
    return content
