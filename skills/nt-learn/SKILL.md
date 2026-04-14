---
name: nt-learn
description: "Use when learning NautilusTrader from scratch or deepening understanding. Provides a structured curriculum from installation to building custom NT components in Python and Rust."
---

# Learn NautilusTrader

## Overview

A structured learning pathway from beginner to NT developer. Walks through installation, examples, concepts, and progressively deeper implementation — from Python strategies to Rust internals to full Rust trading systems.

## Workflow

1. Ask: "What's your current level with NautilusTrader?"
   - **Brand new** → Start at Stage 01
   - **Can run examples** → Start at Stage 03
   - **Can write strategies** → Start at Stage 05
   - **Want to learn Rust internals** → Start at Stage 08
   - **Want to write full Rust trading systems** → Start at Stage 09
   - **Want to build/extend NT** → Start at Stage 10
2. Work through stages sequentially from entry point
3. Each stage has concepts, exercises, and a checkpoint
4. Ask user for local NT path at first source exploration

## Curriculum

| Stage | Topic | Prerequisites |
|-------|-------|--------------|
| 01 | Setup & Installation | None |
| 02 | Running Examples | Stage 01 |
| 03 | Architecture Foundations | Stage 02 |
| 04 | First Strategy | Stage 03 |
| 05 | Backtesting Deep Dive | Stage 04 |
| 06 | Indicators & Actors | Stage 05 |
| 07 | Live Trading | Stage 06 |
| 08 | Rust Internals | Stage 07 |
| 09 | Full Rust Trading | Stage 08 |
| 10 | Building NT | Stage 09 |

## Stage Files

Each stage is in `curriculum/NN-topic.md`. Load the appropriate stage file based on where the user is.
