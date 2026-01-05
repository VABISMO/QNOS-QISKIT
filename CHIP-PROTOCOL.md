Fabrication Protocol for an Integrated Electrically Pumped CQD ASE Emitter Array Coupled with a PMMA/hBN Spin Defect Layer: A Home- and Maker-Laboratory Approach
Abstract

This document presents a complete, self-contained protocol for fabricating an integrated photonic–quantum demonstration chip combining an electrically pumped carbon quantum dot (CQD) high-brightness emitter array exhibiting amplified spontaneous emission (ASE) with a PMMA-coated hexagonal boron nitride (hBN) layer containing optically addressable spin defects.

The design leverages hydrothermal synthesis for CQDs, liquid-phase exfoliation of hBN from powder, and dry stacking of van der Waals heterostructures, all optimized for minimal laboratory infrastructure. Polymer waveguides are incorporated to improve photon transfer efficiency between the CQD emitters and hBN defects, addressing the dominant coupling inefficiency in planar architectures.

While true electrically pumped CQD lasing is not claimed, the platform supports narrowband, high-intensity electroluminescence and ASE, sufficient for optical excitation of hBN spin defects. The resulting device enables room-temperature quantum-optical demonstrations, including spatially resolved excitation and preliminary ODMR measurements, with expected spin coherence times in the microsecond range. Key challenges such as thermal management, emission uniformity, and defect variability are discussed with practical mitigation strategies.

Introduction

Integrated quantum photonic platforms require efficient coupling between compact light sources and solid-state spin defects for applications in quantum sensing, imaging, and information processing. Carbon quantum dots (CQDs) provide tunable visible emission (≈405–532 nm), overlapping well with excitation bands of several defect families in hexagonal boron nitride (hBN), a two-dimensional wide-bandgap material hosting room-temperature spin qubits such as boron vacancies (VB⁻) and carbon-related centers.

Electrically driven CQD devices are well established as LEDs and high-brightness emitters and can exhibit amplified spontaneous emission (ASE) under high current densities. Although stable, reproducible electrically pumped CQD lasers remain an open research challenge, ASE-based emitters already provide sufficient brightness and spectral narrowing for defect excitation.

Van der Waals heterostructures allow straightforward stacking of CQD emitters and hBN layers, but efficient photon transfer requires optical mode control. Polymer waveguides mitigate Lambertian emission losses and enable localized excitation. This protocol starts from biomass-derived CQDs and commercial hBN powder, avoiding complex precursors and vacuum fabrication. Typical CQD yields are 10–20%, and achievable hBN defect densities are ~0.1–0.3 emitters/µm². With waveguides, optical coupling efficiencies of 20–40% are realistic and already represent a substantial improvement over free-space excitation.

Materials and Methods
Section 1: Electrically Pumped Self-Assembled CQD ASE Emitter Array
Materials

Biomass precursor: 3–5 g citric acid or dried orange peels

Solvent: 30–50 mL distilled water

Dopant: 1–2 g urea (nitrogen doping, red-shifts emission)

Hole injection layer: PEDOT:PSS (aqueous dispersion)

Electron transport layer: ZnO nanoparticles (ethanol dispersion)

Substrate: ITO-coated glass slides

Contacts: copper foil or conductive epoxy

Optional optical materials: PMMA, PVA, or PDMS (waveguides / microlenses)

Step 1: Preparation of CQD Precursor Solution (15–30 min)

Grind biomass precursor into fine powder.

Dissolve 3–5 g precursor in 30–50 mL distilled water.

Add 1–2 g urea to improve quantum yield and electronic conductivity.

Stir at 50–60 °C for 10–15 min until homogeneous.

Emission tuning:

Lower concentration → smaller dots → blue/violet (~405 nm)

Higher concentration + higher temperature → green (~520–540 nm)

Step 2: Hydrothermal Synthesis of CQDs (4–6 h)

Transfer solution to a Teflon-lined autoclave (≤70% fill).

Heat at:

180 °C for blue/violet CQDs

200–220 °C for green CQDs
for ~4 h.

Allow to cool naturally to room temperature.

Result: CQDs ~3–5 nm with surface –OH / –COOH groups enabling solution processing and charge injection.

Step 3: Purification (30–60 min + optional dialysis)

Filter through paper to remove aggregates.

Centrifuge at 3000–5000 rpm for 10–15 min.

Optionally dialyze against distilled water for 12–24 h to remove ionic byproducts.

Step 4: Formation of Self-Assembled CQD Emitter Film (1–2 h)

Prepare CQD ink (~5–10 mg/mL in water or ethanol).

Clean ITO substrate (acetone → IPA → DI water).

Spin-coat or drop-cast CQD ink to obtain a 100–200 nm film.

Dry at 60–80 °C for 30 min.

CQDs self-assemble into dense emissive ensembles (~10⁹–10¹¹ dots/cm²).

Step 5: Device Assembly for Electrical Pumping (≈1 h)

Deposit PEDOT:PSS on ITO (≈40–60 nm); bake at 80 °C for 30 min.

Deposit CQD active layer (from Step 4).

Deposit ZnO nanoparticle layer (≈40–60 nm); bake at 80 °C.

Attach copper contacts to top electrode and ITO bottom, forming a p–i–n diode.

Pattern contacts (1–2 mm spacing) for spatially addressable excitation zones.

Step 6: Low-Temperature Annealing (30 min)

Anneal at 150–200 °C for 15–30 min (air or N₂).
Higher temperatures risk CQD degradation and polymer damage.

Step 7: Optional Polymer Waveguide / Microlens Integration (≈1 h)

Prepare PDMS (10:1) or PMMA/PVA solution.

Cast into tape-defined grooves or microchannels above emissive zones.

Cure:

PDMS: 80–100 °C, 30–60 min

PVA/PMMA: air-dry or mild bake

These structures convert diffuse emission into guided or weakly collimated output.

Step 8: Electrical and Optical Testing (≈30 min)

Drive device with DC or pulsed bias (5–20 V).

Observe electroluminescence (405–532 nm).

At high current densities (≈10²–10³ A/cm², preferably pulsed), spectral narrowing and ASE-like behavior may appear.

Important: This regime corresponds to ASE / high-brightness emission, not confirmed lasing.

Expected performance:

External quantum yield: 10–20%

ASE threshold (optical equivalent): ~10² µW

Device area: 1–5 cm²

Section 2: PMMA/hBN Layer with Spin Defects
Materials

hBN powder (100–500 mg)

IPA or NMP (exfoliation solvent)

Substrate: Si/SiO₂ or glass

PMMA 950K A7

Optional defect sources: glucose, UV–ozone

Tools: ultrasonic bath (preferred), spin coater, hot plate, furnace (or shared facility)

Step 1: Liquid-Phase Exfoliation (1–2 h)

Disperse 100–200 mg hBN in 20–50 mL solvent.

Sonicate 1–2 h (or vigorous shaking if unavailable).

Centrifuge 1500–3000 rpm, 30 min.

Collect supernatant with few-layer flakes (≈10–100 nm thick).

Deposit on substrate and dry at 80 °C.

Step 2: Defect Engineering (variable)

Thermal route (preferred, shared facility):

Anneal at 800–1000 °C under Ar/N₂ for 1–2 h.

Lower-tech alternative:

Anneal at ~450–500 °C in air (lower defect density).

UV–ozone exposure (10–30 min) for surface defects.

Carbon-related defects can be promoted by glucose-assisted annealing.

Typical defect density: 0.1–0.3 emitters/µm².
Coherence times: order of microseconds at room temperature.

Step 3: PMMA Coating and Transfer (1–2 h)

Spin-coat PMMA (500 rpm 10 s → 5000 rpm 50 s).

Bake at 160 °C for 5 min.

Optionally transfer PMMA/hBN film onto target substrate via wet or dry transfer.

Section 3: Integrated Chip Assembly with Waveguides
Materials

CQD emitter substrate

PMMA/hBN film

Waveguide material: SU-8 or PDMS

Encapsulation PMMA/epoxy

Optional microwave electrodes

Step 1: Layer Preparation

Prepare CQD emitter array and PMMA/hBN film independently.

Step 2: Waveguide Fabrication (1–2 h)

Spin-coat SU-8 (≈2–5 µm) or cast PDMS.

Pattern via UV mask (SU-8) or tape molds (PDMS).

Cure appropriately.

Target waveguide loss: ~1–5 dB/cm (acceptable).

Step 3: Layer Alignment and Bonding (≈1 h)

Align PMMA/hBN over waveguide outputs.

Dry-transfer using tape or PDMS stamp.

Bond at 100–150 °C for 15–30 min.

Step 4: Contacts and Encapsulation (≈30 min)

Extend electrical contacts if required.

Add microwave electrodes for ODMR.

Encapsulate with PMMA or epoxy.

Step 5: Final Annealing and Testing

Mild anneal: 150 °C, 15 min.

Test electroluminescence, waveguide coupling, and defect fluorescence.

ODMR possible with external microwave source.

Results and Discussion

This architecture demonstrates a realistic integrated photonic–spin platform. CQDs provide electrically driven, spectrally narrowed emission suitable for defect excitation. hBN defects retain room-temperature spin addressability. Polymer waveguides substantially improve photon transfer, with 20–40% coupling efficiencies achievable in practice. Thermal management and emission uniformity remain limiting factors but are mitigated by pulsed operation and modular design.