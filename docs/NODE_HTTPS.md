# HTTPS for the node, in about ten minutes

Why: phone browsers open the microphone (hold-to-talk) and keep the offline copy of the app (the scam check and
benefits interview at home) only on a secure page. On plain `http://<node-address>:8000` neither happens; phones
fall back to the recorder app for voice and keep no copy. The stand-alone site
(https://roshworldwide.github.io/optum-v2/) already works offline after one visit, so this is for the node itself.

You need a domain you control. The example uses `sahayak.roshworldwide.com`; any name under a domain you own works.
The node never needs internet after this: the certificate is fetched once, and on the demo Wi-Fi the node's own DNS
answers the name.

## 1. Get the certificate (once, with internet, on any computer)

Certbot is best supported on macOS and Linux (`brew install certbot` on a Mac); if it will not run on the Windows
node, do this step on another computer and copy the two `.pem` files to the node's `%USERPROFILE%\.sahayak\certbot\`.

```
python -m pip install certbot
certbot certonly --manual --preferred-challenges dns -d sahayak.roshworldwide.com ^
  --config-dir %USERPROFILE%\.sahayak\certbot --work-dir %USERPROFILE%\.sahayak\certbot\work ^
  --logs-dir %USERPROFILE%\.sahayak\certbot\logs --agree-tos -m <your email>
```
(On macOS or Linux, use `~/.sahayak/certbot` and `\` at line ends.)

Certbot prints a TXT record and waits. At your DNS provider (for roshworldwide.com: GoDaddy, My Products, Domain,
DNS, Add New Record), add:

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| TXT | `_acme-challenge.sahayak` | the value certbot printed | 600 seconds (or the lowest offered) |

Wait a minute, check it is visible (`nslookup -type=TXT _acme-challenge.sahayak.roshworldwide.com 8.8.8.8`), then
press Enter in certbot. The certificate lands in `%USERPROFILE%\.sahayak\certbot\live\sahayak.roshworldwide.com\`
(`fullchain.pem`, `privkey.pem`). It lasts 90 days; repeat before it runs out. You may delete the TXT record afterwards.

## 2. Start the node on HTTPS

```
set SAHAYAK_TLS_CERT=%USERPROFILE%\.sahayak\certbot\live\sahayak.roshworldwide.com\fullchain.pem
set SAHAYAK_TLS_KEY=%USERPROFILE%\.sahayak\certbot\live\sahayak.roshworldwide.com\privkey.pem
set SAHAYAK_PUBLIC_HOST=sahayak.roshworldwide.com
set SAHAYAK_PORT=443
set SAHAYAK_HTTP_PORT=80
python -m sahayak
```

## 3. Make the name point at the node on the demo Wi-Fi

Run the node's DNS (`python -m sahayak.node.dns --ip <node-address>`) and set the travel router to hand out the
node as the DNS server (its DHCP settings). Every name, including `sahayak.roshworldwide.com` and the phones'
"is there internet?" checks, now answers with the node, so phones show "Sign in to network" and open Sahayak over
HTTPS. Phones with a private-DNS server forced in their settings bypass this; open the node's address by number
for them (voice then uses the recorder app).

## 4. Check it

- On a phone on the Wi-Fi: `https://sahayak.roshworldwide.com` opens with a padlock; hold-to-talk asks for the
  microphone.
- From the node laptop: `python scripts/check_phone_offline.py https://sahayak.roshworldwide.com/` (one visit, network
  off, then a scam check, a QR check and a benefits interview, all on the phone).
- `/app/node.html` shows "HTTPS" next to the version.
