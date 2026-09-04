# The WordVenture facts scoring rests on

Transcribed from the design document. None of this is in the material the agent receives; it
is what a human needs in order to tell a correct report from a plausible one, and it is why
the false expectations in `answer-key.md` are false.

The agent sees only block names, sprite names, and `TMP_Text` from a scan. The game has no
`[ArtelState]` and no `[ArtelAction]` at all.

## Affinity table

It lives in `Magic Affinity Table.asset` and no scan picks it up. The only way to learn it is
to hit something and read the HP.

| 시전 ↓ / 대상 → | Fire | Ice | Rock | Lightning | Holy | Undead |
| --- | --- | --- | --- | --- | --- | --- |
| Fire | 1.0 | 1.5 | 0.7 | 1.0 | 1.0 | 0.7 |
| Ice | 1.0 | 1.0 | 1.5 | 0.7 | 1.0 | 0.7 |
| Rock | 1.0 | 1.0 | 1.0 | 1.5 | 0.7 | 0.7 |
| Lightning | 1.0 | 1.0 | 1.0 | 1.0 | 1.5 | 0.7 |
| Holy | −1.0 | −1.0 | −1.0 | −2.0 | −2.0 | 3.0 |

A negative multiplier heals, because `TakeHit` only subtracts. The player is always judged as
target type Holy, so Holy cast on the player heals at double. That is the game's only heal.

## Damage

`(10 + 5 × (StagePosition / 2)) × spell 계수 × 상성` — Shoot 1.0, Drop 0.8, Summon 0.67. The
division is integer division, so the per-stage base is 10 / 10 / 15 / 15 / 20.

## Enemies per stage

| 스테이지 | 웨이브 | 적 HP | 속성 |
| --- | --- | --- | --- |
| 0 평원 | 3 | 10 / 20 / 20+10 | Fire |
| 1 바다 | 3 | 20 / 20+30 / 20+30+30 | Ice |
| 2 고원 | 3 | 20 / 20+30 / 20+30+30 | Rock |
| 3 비 | 3 | 20 / 20+30 / 20+30+30 | Lightning |
| 4 보스 | 4 | 25+25 / 25+35 / 25+35+20 / 80 | Holy → Undead |

The final boss `SlimeKing2` is Undead with 80 HP. Holy does 20 × 3.0 = 60, so two casts;
anything else does 20 × 0.7 = 14, so six. The three waves before it are Holy type, so hitting
them with Holy heals them — the counter is Lightning. The boss stage cannot be pushed through
with one element; the affinities have to be learned for real.

## The tutorial interrupts the whole first battle

`TutorialCondition` FLAG_001~014 are wired into battle progress. Every single input brings the
dialogue window back up, and every time it comes up `InteractionLock.IsLocked = true`.

The most dangerous point is right after casting:

- 발동 버튼을 누른다
- 슬롯이 비워지며 FLAG_008 대사가 뜨고 입력이 잠긴다
- `CastSpell` 은 `while (target == null)` 로 무한 대기 중
- 적을 클릭해도 `SelectableObject.OnMouseDown` 이 걸러서 아무 일도 안 일어난다
- FLAG_009·010·011 까지 넘겨야 클릭이 먹는다

A run stops here for good. That is why L1 breaks this stretch out as its own step 17.
