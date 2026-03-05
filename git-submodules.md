# Git Submodules

A guide for adding and maintaining external repositories as submodules in this project.

## Adding a Submodule

```bash
git submodule add <repository-url> <path>
```

Example:

```bash
git submodule add https://github.com/example/some-repo.git lessons/some-repo
```

This creates a `.gitmodules` file (if it doesn't exist) and records the submodule in your root repo at the specified path. Commit the result:

```bash
git add .gitmodules <path>
git commit -m "Add some-repo as submodule"
```

## Cloning This Repo with Submodules

When cloning this repository, include submodules in one step:

```bash
git clone --recurse-submodules <repository-url>
```

Or, if you already cloned without submodules:

```bash
git submodule init
git submodule update
```

## Pulling Upstream Updates to a Submodule

To update a submodule to the latest commit on its default branch:

```bash
git submodule update --remote <path>
```

To update all submodules at once:

```bash
git submodule update --remote
```

After updating, commit the change in the root repo to record the new commit pointer:

```bash
git add <path>
git commit -m "Update some-repo submodule to latest"
```

## Pulling Root Repo Updates (Including Submodule Changes)

When pulling changes that include submodule pointer updates:

```bash
git pull
git submodule update
```

Or in one step:

```bash
git pull --recurse-submodules
```

## Checking Submodule Status

```bash
git submodule status
```

## Removing a Submodule

```bash
git submodule deinit <path>
git rm <path>
git commit -m "Remove some-repo submodule"
```
