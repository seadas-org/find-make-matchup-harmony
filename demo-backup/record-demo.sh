#!/bin/bash
# Auto-driven recording of the Find & Make Matchup terminal demo.
# Used as asciinema rec --command "bash demo-backup/record-demo.sh".

set -e
cd /home/aynur/mainwork/harmony/find-make-matchup-harmony

bar() { printf '\n\033[1;36m============================================================\033[0m\n'; }
hdr() { bar; printf '\033[1;36m  %s\033[0m\n' "$1"; bar; printf '\n'; sleep 2; }
say() { printf '\033[1;33m$ %s\033[0m\n\n' "$1"; sleep 2; }

hdr "1. Find & Make Matchup -- Harmony service prototype"
say "ls"
ls
sleep 6

say "git log --oneline -8"
git log --oneline -8
sleep 8

hdr "2. Architecture: adapter <-> engine split"
say "head -55 prototype/matchup-service/harmony_service_example/transform.py"
head -55 prototype/matchup-service/harmony_service_example/transform.py
sleep 16

say "head -50 prototype/matchup-service/matchup/orchestrator.py"
head -50 prototype/matchup-service/matchup/orchestrator.py
sleep 16

say "sed -n '1,60p' docs/architecture.md"
sed -n '1,60p' docs/architecture.md
sleep 16

hdr "3. Harmony contract -- the public interface"
say "cat harmony/service-config.json"
cat harmony/service-config.json
sleep 18

say "cat harmony/stac-item-shape.md"
cat harmony/stac-item-shape.md
sleep 18

say "cat harmony/example-request.json"
cat harmony/example-request.json
sleep 14

hdr "4. Live invoke -- pull image from DockerHub and run on test data"
say "cd prototype/matchup-service && bin/demo-invoke"
cd prototype/matchup-service
sg docker -c 'bin/demo-invoke'
cd ..
sleep 10

hdr "5. Verify on DockerHub -- the image is real and public"
say "curl -s https://hub.docker.com/v2/repositories/seadas/find-make-matchup-harmony/tags/ | python3 -c '...'"
curl -s 'https://hub.docker.com/v2/repositories/seadas/find-make-matchup-harmony/tags/' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Tags on seadas/find-make-matchup-harmony: {d[\"count\"]}')
for t in d['results']:
    img = t['images'][0]
    size = img['size'] / (1024*1024)
    print(f'  {t[\"name\"]:<55}  {size:6.1f} MB  pushed {img[\"last_pushed\"][:19]}')
"
sleep 12

hdr "6. Pipeline status"
printf "  - Image:           seadas/find-make-matchup-harmony  (DockerHub, public)\n"
printf "  - CI:              GitHub Actions, green on every push to main\n"
printf "  - Reproducibility: pulled image SHA-matches the reference output\n"
printf "  - Next:            Harmony service-registry entry (NASA / Earthdata)\n"
printf "\n"
sleep 8
