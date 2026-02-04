# Proiect de Licență: Mașină Autonomă Electrică (Scara 1:10)
### Sistem de Navigație Autonomă folosind Computer Vision și Sensor Fusion

![Status Proiect](https://img.shields.io/badge/status-In_Lucru-orange)
![Platforma](https://img.shields.io/badge/platforma-Raspberry_Pi_%7C_STM32-blue)
![Limbaje](https://img.shields.io/badge/limbaje-Python_%7C_C-yellow)

> **Notă:** Acest repository conține sursele software și documentația pentru dezvoltarea unui vehicul autonom la scara 1:10, capabil să navigheze într-un mediu urban simulat.

---

## Cuprins
1. [Descrierea Proiectului](#descrierea-proiectului)
2. [Arhitectura Sistemului](#arhitectura-sistemului)
3. [Tehnologii Utilizate](#tehnologii-utilizate)
4. [Roadmap Preliminar](#roadmap-preliminar)
5. [Instalare și Configurare](#instalare-și-configurare)

---

## Descrierea Proiectului

Scopul acestui proiect este proiectarea și implementarea unui sistem complet de conducere autonomă pe un șasiu de automodelism. Sistemul utilizează o arhitectură hibridă de calcul (Split-Computing) pentru a procesa datele vizuale și a controla vehiculul în timp real.

Funcționalitățile principale vizate sunt:
* **Percepție Vizuală Avansată:** Detectarea benzilor de circulație și recunoașterea semnelor de circulație (STOP, Semafor, Limite de viteză) folosind algoritmi de procesare a imaginii.
* **Navigație Globală:** Planificarea traseului optim între două puncte pe o hartă predefinită a unui oraș miniatural (folosind algoritmi de tip Dijkstra/A*).
* **Control în Timp Real:** Menținerea traiectoriei și a vitezei folosind bucle de reglare PID și odometrie.
* **Telemetrie și Monitorizare:** O aplicație PC pentru vizualizarea stării vehiculului, a hărții și a fluxului video procesat.
* **Management Energetic:** Proiectarea unui BMS (Battery Management System) propriu pentru gestionarea acumulatorilor.

---

## Arhitectura Sistemului

Sistemul este împărțit în trei niveluri logice:

1.  **Nivelul Înalt (Percepție & Decizie - Raspberry Pi 4):**
    * Rulează sistemul de operare Linux.
    * Procesează imaginile de la cameră (OpenCV).
    * Interpretează semnele de circulație.
    * Comunică prin Wi-Fi cu aplicația de monitorizare de pe PC.

2.  **Nivelul Jos (Execuție & Senzori - STM32F446RE):**
    * Rulează cod "Bare-metal" sau RTOS.
    * Generează semnalele PWM pentru motor și servodirecție.
    * Citește encoderii pentru odometrie și viteza roților.
    * Execută buclele de control PID pentru stabilitate.

3.  **Interfața Utilizator (PC Dashboard):**
    * Permite selectarea rutei (Start -> Finish).
    * Afișează date critice (Viteză, Unghi virare, SoC Baterie).

```mermaid
graph TD
    PC[PC Dashboard] -- WiFi / TCP --> RPi[Raspberry Pi 4]
    RPi -- USB UART --> STM[STM32 Nucleo]
    Cam[Camera Video] -- CSI/USB --> RPi
    STM -- PWM --> Actuatori[Motor & Servo]
    Encoderi -- Intererupt --> STM
