#!/usr/bin/env python3
"""
Naturalize scraped data to make it less obvious it was scraped.

Transformations:
1. Reformulate descriptions (AI-based, same content/length)
2. Modify image dimensions slightly (resize URLs)
3. Add year to race names if missing
4. Normalize organizer company names (doo -> d.o.o., etc.)
"""

import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import random

from ai.llm import OllamaClient
from common.model import Event, Race

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class DataNaturalizer:
    """Naturalize scraped race data."""
    
    def __init__(self, use_ai: bool = True, ai_provider: str = 'ollama'):
        self.use_ai = use_ai
        self.ai_provider = ai_provider
        self.llm = None
        self.openai_client = None
        
        if use_ai:
            if ai_provider == 'openai' and OPENAI_AVAILABLE:
                # Use OpenAI API
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    print("✓ Using OpenAI for description reformulation")
                else:
                    print("⚠️ OPENAI_API_KEY not found, falling back to Ollama")
                    ai_provider = 'ollama'
            
            if ai_provider == 'ollama':
                try:
                    self.llm = OllamaClient()
                    print("✓ Using Ollama for description reformulation")
                except Exception as e:
                    print(f"⚠️ Error initializing Ollama client: {e}")
                    print("⚠️ Falling back to non-AI mode")
                    self.use_ai = False
        
        # Company name normalizations (Serbian/Balkan business entities)
        self.company_normalizations = {
            r'\bdoo\b': 'd.o.o',
            r'\bDOO\b': 'D.O.O',
            r'\bad\b': 'a.d',
            r'\bAD\b': 'A.D',
            r'\bjp\b': 'j.p',
            r'\bJP\b': 'J.P',
            r'\bkd\b': 'k.d',
            r'\bKD\b': 'K.D',
            r'\bpo\b': 'p.o',
            r'\bPO\b': 'P.O',
        }
    
    def reformulate_description(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Reformulate description to sound more natural while keeping same content.
        
        Args:
            text: Original description
            max_length: Target length (approximately same as original if None)
            
        Returns:
            Reformulated description
        """
        if not text or len(text) < 20:
            return text
        
        if not self.use_ai:
            # Fallback: Just make minor punctuation/spacing changes
            result = text
            result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
            result = re.sub(r'\.\.+', '.', result)  # Single dots only
            result = re.sub(r'\s+([.,!?;:])', r'\1', result)  # Fix spacing before punctuation
            return result.strip()
        
        target_length = max_length or len(text)
        min_length = int(target_length * 0.9)
        max_length_limit = int(target_length * 1.1)
        
        prompt = f"""Prepiši sledeći opis trke tako da zvuči prirodnije, ali zadrži isti sadržaj i informacije.
Ciljana dužina: {min_length}-{max_length_limit} karaktera (original: {len(text)} karaktera).

PRAVILA:
- Zadrži SVE bitne informacije (datumi, imena, lokacije, razdalje, itd.)
- Promeni samo redosled rečenica i formulaciju
- Nemoj dodavati nove informacije
- Nemoj koristiti marketing jezik ili superlative koji nisu u originalu
- Piši prirodnim, informativnim stilom

ORIGINAL TEKST:
{text}

PREPISANI TEKST:"""

        try:
            reformulated = ''
            
            if self.openai_client:
                # Use OpenAI API
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Ti si asistent koji prepisuje tekstove da zvuče prirodnije, ali zadržava isti sadržaj."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=max_length_limit + 200
                )
                reformulated = response.choices[0].message.content.strip()
            
            elif self.llm:
                # Use Ollama
                response = self.llm.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=max_length_limit + 200
                )
                reformulated = response.get('message', {}).get('content', '').strip()
            
            # If AI response is too different in length, use fallback
            if not reformulated or abs(len(reformulated) - target_length) > target_length * 0.3:
                print(f"⚠️ AI reformulation length mismatch ({len(reformulated)} vs {target_length}), using fallback")
                return self._reformulate_without_ai(text)
            
            # Fix grammar and diacritics in AI-generated text
            reformulated = self._fix_grammar_and_diacritics(reformulated)
            
            return reformulated
            
        except Exception as e:
            print(f"⚠️ Error reformulating description: {e}")
            # Fallback to intelligent reformulation without AI
            return self._reformulate_without_ai(text)
    
    def modify_image_dimensions(self, image_url: str) -> str:
        """
        Modify image URL to change dimensions slightly.
        
        For common image hosting services, add/modify resize parameters.
        For others, add query parameters that might trigger resizing.
        
        Args:
            image_url: Original image URL
            
        Returns:
            Modified image URL
        """
        if not image_url:
            return image_url
        
        parsed = urlparse(image_url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Random dimension adjustments (±1-5 pixels)
        width_adjust = random.randint(-5, 5)
        height_adjust = random.randint(-5, 5)
        
        # Common dimension base sizes
        base_width = random.choice([800, 1200, 1600])
        base_height = random.choice([600, 900, 1200])
        
        new_width = base_width + width_adjust
        new_height = base_height + height_adjust
        
        # Detect hosting service and adjust accordingly
        hostname = parsed.hostname or ''
        
        if 'facebook.com' in hostname or 'fbcdn.net' in hostname:
            # Facebook CDN - modify dimension parameters
            query_params['width'] = [str(new_width)]
            query_params['height'] = [str(new_height)]
        
        elif 'cloudinary.com' in hostname:
            # Cloudinary - modify transformation parameters
            path_parts = parsed.path.split('/')
            for i, part in enumerate(path_parts):
                if part.startswith('w_') or part.startswith('h_'):
                    # Replace width/height in path
                    if part.startswith('w_'):
                        path_parts[i] = f'w_{new_width}'
                    else:
                        path_parts[i] = f'h_{new_height}'
            parsed = parsed._replace(path='/'.join(path_parts))
        
        elif 'imgur.com' in hostname:
            # Imgur - add size suffix
            path = parsed.path
            if not path.endswith(('s.jpg', 'm.jpg', 'l.jpg', 'h.jpg')):
                # Add medium size suffix
                path = path.rsplit('.', 1)
                if len(path) == 2:
                    parsed = parsed._replace(path=f"{path[0]}m.{path[1]}")
        
        else:
            # Generic approach: add resize parameters
            query_params['w'] = [str(new_width)]
            query_params['h'] = [str(new_height)]
        
        # Reconstruct URL with modified query
        new_query = urlencode(query_params, doseq=True)
        result = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return result
    
    def add_year_to_name(self, name: str, event_date: Optional[datetime]) -> str:
        """
        Add year to race name if not already present.
        
        Args:
            name: Race name
            event_date: Event date
            
        Returns:
            Race name with year (if applicable)
        """
        if not name or not event_date:
            return name
        
        year = event_date.year if hasattr(event_date, 'year') else None
        if not year:
            return name
        
        # Check if year already in name
        if str(year) in name or str(year - 1) in name or str(year + 1) in name:
            return name
        
        # Check for other year patterns (2-digit)
        year_2digit = str(year)[-2:]
        if f"'{year_2digit}" in name or f"'{year_2digit}" in name:
            return name
        
        # Add year at the end
        # Common patterns: "Race Name 2026" or "Race Name '26"
        return f"{name} {year}"
    
    def _fix_grammar_and_diacritics(self, text: str) -> str:
        """
        Fix grammar issues and missing Serbian diacritics.
        
        Args:
            text: Text to fix
            
        Returns:
            Corrected text
        """
        if not text:
            return text
        
        # Common Serbian words with missing diacritics
        diacritic_corrections = {
            # č replacements
            r'\bpocetnike\b': 'početnike',
            r'\bpocetnika\b': 'početnika',
            r'\bpocetak\b': 'početak',
            r'\bpocinje\b': 'počinje',
            r'\b([Uu])cesnika\b': r'\1česnika',
            r'\b([Uu])cesnike\b': r'\1česnike',
            r'\b([Uu])cesnici\b': r'\1česnici',
            r'\b([Uu])cesce\b': r'\1češće',
            r'\b([Uu])kljucuje\b': r'\1ključuje',
            r'\buklju([cč])en([aeiou])\b': r'uključen\2',
            r'\bznacajn([aeiou])\b': r'značajn\1',
            r'\bisklju([cč])iv([aeiou])\b': r'isključiv\2',
            r'\btocka\b': 'tačka',
            r'\btacka\b': 'tačka',
            r'\bmesec\b': 'mesec',  # This is correct without diacritic
            r'\b([Mm])ogucnost([aeiou]?)\b': r'\1ogućnost\2',
            
            # ć replacements
            r'\bkoli([cč])in([aeiou])\b': r'količin\2',
            r'\b([Vv])ise([cč]?)\b': r'\1iše',
            r'\bteci\b': 'teći',
            r'\bpoci\b': 'poći',
            
            # š replacements
            r'\b([Nn])ajlep([sz])([aeioum])\b': r'\1ajlepš\3',
            r'\bnajlepsem\b': 'najlepšem',
            r'\blep([sz])([aeioum])\b': r'lepš\2',
            r'\bprelepe\b': 'prelepe',  # Keep as-is (Ekavian)
            r'\bstap\b': 'štap',
            r'\b([Ss])to\b': r'\1to',  # This is correct
            r'\bdal([sz])e\b': 'dalje',
            
            # ž replacements
            r'\bdr([zž])av([aeiou])\b': r'držav\2',
            r'\b([Mm])o([zž])e\b': r'\1ože',
            r'\btakmi([cč])enj([aeiou])\b': r'takmičenj\2',
            r'\b([Uu])zivaj([aeiou])\b': r'\1živaj\2',
            
            # đ replacements (rare in trail running context)
            r'\bme([dđ])u\b': 'među',
            
            # Common typos
            r'\bstarni\b': 'startni',
            r'\bodrzava\b': 'održava',
            r'\bse odrzava\b': 'se održava',
            r'\bse organiziju\b': 'se organizuje',
            r'\bprolazii\b': 'prolazi',
            r'\bDd\+': 'D+',  # Fix D+ notation
            r'\bD \+': 'D+',
            r'\bd\+': 'D+',
            r'\bd \+': 'D+',
        }
        
        result = text
        
        # Apply diacritic corrections
        for pattern, replacement in diacritic_corrections.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Fix capitalization after periods
        def capitalize_after_period(match):
            return match.group(1) + match.group(2).upper()
        
        result = re.sub(r'([.!?]\s+)([a-zа-ш])', capitalize_after_period, result)
        
        # Fix double spaces
        result = re.sub(r'\s+', ' ', result)
        
        # Fix spacing around common separators
        result = re.sub(r'\s*([,:;])\s*', r'\1 ', result)
        result = re.sub(r'\s+([.!?])', r'\1', result)
        
        return result.strip()
    
    def _reformulate_without_ai(self, text: str) -> str:
        """
        Reformulate text without AI by rearranging sentences and using synonyms.
        
        Args:
            text: Original description
            
        Returns:
            Reformulated description
        """
        if not text or len(text) < 20:
            return text
        
        result = text
        replacements_applied = 0
        max_replacements = 2  # Apply up to 2 synonym replacements
        
        # Apply some synonym replacements (alternating to vary style)
        replacements = [
            ('se održava', 'se organizuje'),
            ('prolaze kroz', 'vode kroz'),
            ('prolazi kroz', 'vodi kroz'),
            ('prelepe', 'lijepe'),
            ('lijepe', 'prelepe'),
            ('distanca', 'udaljenost'),
            ('udaljenost', 'distanca'),
            ('značajne', 'važne'),
            ('važne', 'značajne'),
            ('koji ima', 'sadrži'),
            ('ima', 'obuhvata'),
        ]
        
        for old, new in replacements:
            if old in result and replacements_applied < max_replacements:
                # Replace only first occurrence
                result = result.replace(old, new, 1)
                replacements_applied += 1
        
        # Normalize whitespace
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\.\.+', '.', result)
        result = re.sub(r'\s+([.,!?;:])', r'\1', result)
        
        # Rearrange sentence structure slightly
        sentences = re.split(r'([.!?]+)', result)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Keep first and last sentence in place (usually important info)
        # but try to reorder middle ones
        if len(sentences) > 6 and len(sentences) % 2 != 0:  # Multiple sentences
            # Try to swap 2nd and 3rd sentences if they exist
            try:
                sent_pairs = []
                for i in range(0, len(sentences), 2):
                    if i+1 < len(sentences):
                        sent_pairs.append([sentences[i], sentences[i+1]])
                    else:
                        sent_pairs.append([sentences[i]])
                
                # Reorder: keep first, swap middle ones, keep last
                if len(sent_pairs) > 3:
                    sent_pairs[1], sent_pairs[2] = sent_pairs[2], sent_pairs[1]
                
                # Flatten back
                result_sentences = []
                for pair in sent_pairs:
                    result_sentences.extend(pair)
                result = ''.join(result_sentences)
            except:
                pass
        
        # Fix spacing around punctuation
        result = re.sub(r'\s+([.!?])', r'\1', result)
        
        # Apply grammar and diacritic corrections
        result = self._fix_grammar_and_diacritics(result)
        
        return result.strip()
    
    def normalize_organizer(self, organizer: str) -> str:
        """
        Normalize organizer company name.
        
        Converts abbreviated company types to proper format:
        - doo -> d.o.o.
        - ad -> a.d.
        - etc.
        
        Args:
            organizer: Original organizer name
            
        Returns:
            Normalized organizer name
        """
        if not organizer:
            return organizer
        
        result = organizer
        for pattern, replacement in self.company_normalizations.items():
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def naturalize_race(self, race: Race, event_date: Optional[datetime]) -> Race:
        """
        Naturalize a single race entry.
        
        Args:
            race: Race object
            event_date: Event date for adding year to name
            
        Returns:
            Naturalized race object
        """
        # Create a copy of race data
        race_data = race.model_dump()
        
        # 1. Add year to name if missing
        if race_data.get('name'):
            race_data['name'] = self.add_year_to_name(race_data['name'], event_date)
        
        # 2. Reformulate description
        if race_data.get('description'):
            original_desc = race_data['description']
            race_data['description'] = self.reformulate_description(original_desc)
            if race_data['description'] != original_desc:
                print(f"  ✓ Reformulated description for {race_data['name']}")
        
        # 3. Normalize organizer
        if race_data.get('organizer'):
            original_org = race_data['organizer']
            race_data['organizer'] = self.normalize_organizer(original_org)
            if race_data['organizer'] != original_org:
                print(f"  ✓ Normalized organizer: {original_org} -> {race_data['organizer']}")
        
        # Reconstruct Race object
        return Race(**race_data)
    
    def naturalize_event(self, event: Event) -> Event:
        """
        Naturalize a single event (including all races).
        
        Args:
            event: Event object
            
        Returns:
            Naturalized event object
        """
        # Create a copy of event data
        event_data = event.model_dump()
        
        print(f"\n📝 Naturalizing: {event_data['name']}")
        
        # 1. Reformulate event description
        if event_data.get('description'):
            original_desc = event_data['description']
            event_data['description'] = self.reformulate_description(original_desc)
            if event_data['description'] != original_desc:
                print(f"  ✓ Reformulated event description")
        
        # 2. Modify image URL
        if event_data.get('image_url'):
            original_url = str(event_data['image_url'])
            event_data['image_url'] = self.modify_image_dimensions(original_url)
            if event_data['image_url'] != original_url:
                print(f"  ✓ Modified image dimensions")
        
        # 3. Normalize organizer
        if event_data.get('organizer'):
            original_org = event_data['organizer']
            event_data['organizer'] = self.normalize_organizer(original_org)
            if event_data['organizer'] != original_org:
                print(f"  ✓ Normalized organizer: {original_org} -> {event_data['organizer']}")
        
        # 4. Naturalize all races
        if event_data.get('races'):
            naturalized_races = []
            for race_data in event_data['races']:
                race = Race(**race_data)
                naturalized_race = self.naturalize_race(
                    race, 
                    event_data.get('date')
                )
                naturalized_races.append(naturalized_race.model_dump())
            event_data['races'] = naturalized_races
        
        # Reconstruct Event object
        return Event(**event_data)
    
    def naturalize_file(self, input_file: Path, output_file: Path):
        """
        Naturalize all events in a JSON file.
        
        Args:
            input_file: Input JSON file path
            output_file: Output JSON file path
        """
        print(f"📖 Loading data from {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = []
        if isinstance(data, list):
            events = [Event(**e) for e in data]
        elif isinstance(data, dict) and 'events' in data:
            events = [Event(**e) for e in data['events']]
        else:
            raise ValueError("Unknown JSON format")
        
        print(f"📊 Found {len(events)} events to naturalize")
        
        naturalized_events = []
        for i, event in enumerate(events, 1):
            print(f"\n[{i}/{len(events)}]", end=' ')
            naturalized_event = self.naturalize_event(event)
            naturalized_events.append(naturalized_event)
        
        # Save naturalized data
        print(f"\n\n💾 Saving naturalized data to {output_file}")
        
        output_data = [e.model_dump() for e in naturalized_events]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ Naturalization complete! Saved {len(naturalized_events)} events")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Naturalize scraped race data')
    parser.add_argument('input_file', help='Input JSON file (e.g., races.json)')
    parser.add_argument('-o', '--output', help='Output file (default: input_file with _naturalized suffix)')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI reformulation')
    parser.add_argument('--ai-provider', choices=['ollama', 'openai'], default='ollama', 
                        help='AI provider to use (default: ollama)')
    
    args = parser.parse_args()
    
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    if args.output:
        output_file = Path(args.output)
    else:
        # Default: add _naturalized suffix
        output_file = input_file.parent / f"{input_file.stem}_naturalized{input_file.suffix}"
    
    naturalizer = DataNaturalizer(
        use_ai=not args.no_ai,
        ai_provider=args.ai_provider
    )
    naturalizer.naturalize_file(input_file, output_file)


if __name__ == '__main__':
    main()
