import os
import re
import json
import time
import wave
import urllib.request
import urllib.parse

SPEAKER_ID = 3  # ずんだもん (ノーマル)
VOICEVOX_HOST = "http://127.0.0.1:50021"
INPUT_MD = r"d:\アリコレ作業用フォルダ\Antigravity\AI関連著名人リスト\ai_100_md.md"
OUTPUT_DIR = r"d:\アリコレ作業用フォルダ\Antigravity\AI関連著名人リスト\voice_output_zundamon"

def parse_script(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()
    items = []
    
    current_category = ""
    last_person_num = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        cat_match = re.match(r"^\*\*【(\d+)\.\s*(.+?)】\*\*", line)
        if cat_match:
            current_category = cat_match.group(2)
            i += 1
            continue

        if line == "**【イントロダクション】**":
            intro_text = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("---") and not lines[i].strip().startswith("**【"):
                l = lines[i].strip()
                if l and not l.startswith("（ナレーター）"):
                    l = l.strip("「」")
                    intro_text.append(l)
                i += 1
            items.append({
                "filename": "000_イントロダクション.wav",
                "label": "イントロダクション",
                "text": " ".join(intro_text)
            })
            continue

        if line == "**【アウトロダクション】**":
            outro_text = []
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if l and not l.startswith("（ナレーター）"):
                    l = l.strip("「」")
                    outro_text.append(l)
                i += 1
            items.append({
                "filename": "101_アウトロダクション.wav",
                "label": "アウトロダクション",
                "text": " ".join(outro_text)
            })
            break

        if line == "（ナレーター）":
            i += 1
            if i < len(lines):
                narrator_text = lines[i].strip().strip("「」")
                items.append({
                    "filename": f"{last_person_num:03d}_b_案内_{current_category[:10]}.wav",
                    "label": f"章案内: {current_category}",
                    "text": narrator_text
                })
            i += 1
            continue

        person_match = re.match(r"^\s*(\d+)\.\s*(.+)", line)
        if person_match:
            num = int(person_match.group(1))
            last_person_num = num
            content = person_match.group(2).strip()
            name_match = re.match(r"^([^。、]+)[。、](.+)", content)
            if name_match:
                name = name_match.group(1).strip()
            else:
                name = f"人物_{num}"
            clean_name = name.replace("・", "_").replace(" ", "_").replace("（", "_").replace("）", "")
            items.append({
                "filename": f"{num:03d}_{clean_name}.wav",
                "label": f"No.{num:03d} {name}",
                "text": content
            })
            i += 1
            continue

        i += 1

    return items

def synthesize(text, speaker_id):
    # 1. audio_query
    q = urllib.parse.urlencode({'text': text, 'speaker': speaker_id})
    query_req = urllib.request.Request(f"{VOICEVOX_HOST}/audio_query?{q}", method='POST')
    with urllib.request.urlopen(query_req) as res:
        query_data = res.read()
    
    # 2. synthesis
    synth_req = urllib.request.Request(
        f"{VOICEVOX_HOST}/synthesis?speaker={speaker_id}",
        data=query_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(synth_req) as res:
        return res.read()

def create_silence(duration_sec, sample_rate=24000):
    num_samples = int(sample_rate * duration_sec)
    return b'\x00\x00' * num_samples  # 16-bit mono 0-samples

def combine_wavs(wav_paths, output_combined_path, pause_sec=0.8):
    if not wav_paths:
        return
    with wave.open(wav_paths[0], 'rb') as first_wav:
        params = first_wav.getparams()
    
    silence_frames = create_silence(pause_sec, params.framerate)
    
    with wave.open(output_combined_path, 'wb') as outfile:
        outfile.setparams(params)
        for idx, p in enumerate(wav_paths):
            with wave.open(p, 'rb') as w:
                outfile.writeframes(w.readframes(w.getnframes()))
            if idx < len(wav_paths) - 1:
                outfile.writeframes(silence_frames)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    items = parse_script(INPUT_MD)
    print(f"Total items to generate: {len(items)}")

    generated_files = []
    total = len(items)
    start_time = time.time()

    for idx, item in enumerate(items, 1):
        out_path = os.path.join(OUTPUT_DIR, item["filename"])
        print(f"[{idx}/{total}] 生成中: {item['label']} ({len(item['text'])}文字)...", end=" ", flush=True)
        t0 = time.time()
        try:
            audio_bytes = synthesize(item["text"], SPEAKER_ID)
            with open(out_path, "wb") as f:
                f.write(audio_bytes)
            elapsed = time.time() - t0
            print(f"完了 ({elapsed:.2f}秒)")
            generated_files.append(out_path)
        except Exception as e:
            print(f"エラー: {e}")

    total_time = time.time() - start_time
    print(f"\n全 {len(generated_files)} ファイルの個別生成が完了しました！ (所要時間: {total_time:.1f}秒)")

    # 全結合ファイルの作成
    print("全編結合音声を作成中...", end=" ", flush=True)
    combined_path = os.path.join(OUTPUT_DIR, "000_全編結合_AI分野の重要人物100人_ずんだもん.wav")
    combine_wavs(generated_files, combined_path, pause_sec=0.8)
    print("完了！")
    print(f"結合ファイル: {combined_path}")

if __name__ == "__main__":
    main()
